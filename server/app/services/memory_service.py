"""Agent memory service - persistent memory storage with search, pruning, and stats."""

import uuid

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory

logger = structlog.get_logger()


class MemoryService:
    """Manages agent memories with text search, importance ranking, and pruning."""

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    async def store_memory(
        self,
        db: AsyncSession,
        agent_id: uuid.UUID,
        content: str,
        category: str,
        importance: int = 5,
        metadata: dict | None = None,
    ) -> Memory:
        """Store a new memory for an agent."""
        importance = max(1, min(10, importance))  # clamp to 1-10

        memory = Memory(
            agent_id=agent_id,
            content=content,
            category=category,
            importance=importance,
            metadata_=metadata or {},
        )
        db.add(memory)
        await db.flush()

        logger.info(
            "memory_stored",
            memory_id=str(memory.id),
            agent_id=str(agent_id),
            category=category,
            importance=importance,
        )
        return memory

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search_memories(
        self,
        db: AsyncSession,
        agent_id: uuid.UUID,
        query: str,
        category: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Search memories using SQL LIKE for basic text matching.

        Results are sorted by importance (desc) then recency (desc).
        """
        conditions = [
            Memory.agent_id == agent_id,
            Memory.is_deleted.is_(False),
            Memory.content.ilike(f"%{query}%"),
        ]
        if category:
            conditions.append(Memory.category == category)

        result = await db.execute(
            select(Memory)
            .where(and_(*conditions))
            .order_by(Memory.importance.desc(), Memory.created_at.desc())
            .limit(limit)
        )
        memories = result.scalars().all()

        return [self._to_dict(m) for m in memories]

    # ------------------------------------------------------------------
    # Get
    # ------------------------------------------------------------------

    async def get_memories(
        self,
        db: AsyncSession,
        agent_id: uuid.UUID,
        category: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get memories for an agent, sorted by importance then recency."""
        conditions = [
            Memory.agent_id == agent_id,
            Memory.is_deleted.is_(False),
        ]
        if category:
            conditions.append(Memory.category == category)

        result = await db.execute(
            select(Memory)
            .where(and_(*conditions))
            .order_by(Memory.importance.desc(), Memory.created_at.desc())
            .limit(limit)
        )
        return [self._to_dict(m) for m in result.scalars().all()]

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_memory(
        self,
        db: AsyncSession,
        memory_id: uuid.UUID,
        content: str | None = None,
        importance: int | None = None,
    ) -> dict | None:
        """Update a memory's content and/or importance."""
        result = await db.execute(
            select(Memory).where(Memory.id == memory_id, Memory.is_deleted.is_(False))
        )
        memory = result.scalar_one_or_none()
        if not memory:
            return None

        if content is not None:
            memory.content = content
        if importance is not None:
            memory.importance = max(1, min(10, importance))

        await db.flush()

        logger.info("memory_updated", memory_id=str(memory_id))
        return self._to_dict(memory)

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_memory(self, db: AsyncSession, memory_id: uuid.UUID) -> bool:
        """Soft-delete a single memory."""
        result = await db.execute(
            select(Memory).where(Memory.id == memory_id, Memory.is_deleted.is_(False))
        )
        memory = result.scalar_one_or_none()
        if not memory:
            return False

        memory.soft_delete()
        await db.flush()

        logger.info("memory_deleted", memory_id=str(memory_id))
        return True

    async def clear_agent_memories(self, db: AsyncSession, agent_id: uuid.UUID) -> int:
        """Soft-delete all memories for an agent. Returns count deleted."""
        result = await db.execute(
            select(Memory).where(
                Memory.agent_id == agent_id,
                Memory.is_deleted.is_(False),
            )
        )
        memories = list(result.scalars().all())
        count = len(memories)

        for memory in memories:
            memory.soft_delete()

        await db.flush()

        logger.info("memory_agent_cleared", agent_id=str(agent_id), count=count)
        return count

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_memory_stats(self, db: AsyncSession, agent_id: uuid.UUID) -> dict:
        """Get memory statistics for an agent."""
        base_filter = and_(Memory.agent_id == agent_id, Memory.is_deleted.is_(False))

        # Total count
        count_result = await db.execute(
            select(func.count(Memory.id)).where(base_filter)
        )
        total_count = count_result.scalar() or 0

        # Count by category
        cat_result = await db.execute(
            select(Memory.category, func.count(Memory.id))
            .where(base_filter)
            .group_by(Memory.category)
        )
        categories = dict(cat_result.all())

        # Average importance
        avg_result = await db.execute(
            select(func.avg(Memory.importance)).where(base_filter)
        )
        avg_importance = float(avg_result.scalar() or 0)

        # Approximate storage (character count)
        storage_result = await db.execute(
            select(func.sum(func.length(Memory.content))).where(base_filter)
        )
        total_chars = int(storage_result.scalar() or 0)

        return {
            "agent_id": str(agent_id),
            "total_count": total_count,
            "categories": categories,
            "avg_importance": round(avg_importance, 2),
            "total_characters": total_chars,
            "estimated_storage_kb": round(total_chars / 1024, 2),
        }

    # ------------------------------------------------------------------
    # Pruning
    # ------------------------------------------------------------------

    async def prune_old_memories(
        self,
        db: AsyncSession,
        agent_id: uuid.UUID,
        keep_count: int = 100,
        min_importance: int = 3,
    ) -> int:
        """Prune low-importance memories beyond the keep count.

        Keeps the top `keep_count` memories (by importance desc, recency desc).
        Deletes remaining memories with importance below `min_importance`.
        """
        # Get all memories sorted by importance desc, recency desc
        result = await db.execute(
            select(Memory)
            .where(Memory.agent_id == agent_id, Memory.is_deleted.is_(False))
            .order_by(Memory.importance.desc(), Memory.created_at.desc())
        )
        all_memories = list(result.scalars().all())

        if len(all_memories) <= keep_count:
            return 0

        # Memories beyond the keep window
        candidates = all_memories[keep_count:]
        pruned = 0

        for memory in candidates:
            if memory.importance < min_importance:
                memory.soft_delete()
                pruned += 1

        if pruned > 0:
            await db.flush()

        logger.info(
            "memory_pruned",
            agent_id=str(agent_id),
            pruned=pruned,
            total=len(all_memories),
            kept=len(all_memories) - pruned,
        )
        return pruned

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dict(memory: Memory) -> dict:
        return {
            "id": str(memory.id),
            "agent_id": str(memory.agent_id),
            "content": memory.content,
            "category": memory.category,
            "importance": memory.importance,
            "metadata": memory.metadata_,
            "created_at": memory.created_at.isoformat(),
            "updated_at": memory.updated_at.isoformat(),
        }


memory_service = MemoryService()
