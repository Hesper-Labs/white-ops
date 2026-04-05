import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Plus, Search, Trash2 } from "lucide-react";
import { knowledgeApi } from "../api/endpoints";
import { formatDate } from "../lib/utils";
import toast from "react-hot-toast";

export default function Knowledge() {
  const [showCreate, setShowCreate] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["knowledge", searchQuery, selectedCategory],
    queryFn: () =>
      knowledgeApi.list({
        ...(searchQuery ? { search: searchQuery } : {}),
        ...(selectedCategory ? { category: selectedCategory } : {}),
      }),
  });

  const { data: categoriesData } = useQuery({
    queryKey: ["knowledge-categories"],
    queryFn: () => knowledgeApi.categories(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => knowledgeApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge"] });
      toast.success("Entry deleted");
    },
  });

  const items = data?.data ?? [];
  const categories = categoriesData?.data ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Knowledge Base</h1>
        <button
          className="btn-primary flex items-center gap-2"
          onClick={() => setShowCreate(true)}
        >
          <Plus className="h-4 w-4" />
          Add Entry
        </button>
      </div>

      {/* Search & Filter */}
      <div className="flex gap-4 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-surface-400" />
          <input
            className="input pl-10"
            placeholder="Search knowledge base..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <select
          className="input w-48"
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
        >
          <option value="">All Categories</option>
          {categories.map((cat: any) => (
            <option key={cat.category as string} value={cat.category as string}>
              {cat.category as string} ({cat.count as number})
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      ) : items.length === 0 ? (
        <div className="card p-12 text-center">
          <BookOpen className="h-12 w-12 text-surface-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-surface-700">
            Knowledge base is empty
          </h3>
          <p className="text-surface-400 mt-1">
            Add shared knowledge that agents can reference during task execution.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item: any) => (
            <div key={item.id as string} className="card p-5">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold">{item.title as string}</h3>
                    <span className="badge-blue">{item.category as string}</span>
                  </div>
                  <p className="text-sm text-surface-500 line-clamp-2">
                    {item.content as string}
                  </p>
                  <div className="flex items-center gap-4 mt-2">
                    {((item.tags as string[]) || []).map((tag: string) => (
                      <span key={tag} className="text-xs text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
                        {tag}
                      </span>
                    ))}
                    <span className="text-xs text-surface-400">
                      {formatDate(item.created_at as string)}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => deleteMutation.mutate(item.id as string)}
                  className="text-surface-300 hover:text-red-500 ml-4"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && <CreateKnowledgeModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}

function CreateKnowledgeModal({ onClose }: { onClose: () => void }) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [category, setCategory] = useState("general");
  const [tagsStr, setTagsStr] = useState("");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => knowledgeApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge"] });
      toast.success("Knowledge entry added");
      onClose();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      title,
      content,
      category,
      tags: tagsStr.split(",").map((t) => t.trim()).filter(Boolean),
    });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="card p-6 w-full max-w-lg">
        <h2 className="text-lg font-semibold mb-4">Add Knowledge Entry</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Title</label>
            <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Content</label>
            <textarea className="input" rows={6} value={content} onChange={(e) => setContent(e.target.value)} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Category</label>
              <select className="input" value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="general">General</option>
                <option value="procedures">Procedures</option>
                <option value="policies">Policies</option>
                <option value="contacts">Contacts</option>
                <option value="technical">Technical</option>
                <option value="templates">Templates</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Tags (comma separated)</label>
              <input className="input" value={tagsStr} onChange={(e) => setTagsStr(e.target.value)} placeholder="hr, onboarding" />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancel</button>
            <button type="submit" className="btn-primary flex-1" disabled={mutation.isPending}>
              {mutation.isPending ? "Adding..." : "Add Entry"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
