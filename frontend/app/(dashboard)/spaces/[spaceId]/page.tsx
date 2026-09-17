'use client';
import { useEffect, useState, use } from 'react';
import { fetchApi } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

export default function SpaceDetail({ params }: { params: Promise<{ spaceId: string }> }) {
  const { spaceId } = use(params);
  const [space, setSpace] = useState<any>(null);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [learningGoal, setLearningGoal] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      fetchApi(`/spaces/${spaceId}`),
      fetchApi(`/spaces/${spaceId}/projects`)
    ])
    .then(([spaceData, projectsData]) => {
      setSpace(spaceData);
      setProjects(projectsData);
      setError(null);
    })
    .catch(err => setError(err.message))
    .finally(() => setLoading(false));
  };
  
  const loadProjects = () => {
    fetchApi(`/spaces/${spaceId}/projects`)
      .then(setProjects)
      .catch(err => console.error("Failed to refresh projects:", err));
  };

  useEffect(() => {
    loadData();
  }, [spaceId]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);
    try {
      await fetchApi(`/spaces/${spaceId}/projects`, {
        method: 'POST',
        body: JSON.stringify({ 
          name, 
          description: description || null, 
          learning_goal: learningGoal || null 
        })
      });
      setName('');
      setDescription('');
      setLearningGoal('');
      loadProjects();
    } catch (err: any) {
      setCreateError(err.message);
    } finally {
      setCreating(false);
    }
  };

  if (loading) return <div className="p-6 text-gray-500">Loading space details...</div>;
  if (error) return <div className="p-6 text-red-600">Error: {error}</div>;
  if (!space) return <div className="p-6">Space not found</div>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-6">
        <Link href="/spaces" className="text-sm text-blue-600 hover:underline">&larr; Back to Spaces</Link>
        <h1 className="text-3xl font-bold mt-2">{space.name}</h1>
        {space.description && <p className="text-gray-600 mt-2">{space.description}</p>}
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2">
          <h2 className="text-2xl font-semibold mb-4">Projects</h2>
          {projects.length === 0 ? (
            <div className="p-8 border border-dashed rounded-lg text-center text-gray-500">
              You don't have any Projects in this Space yet.
            </div>
          ) : (
            <ul className="space-y-3">
              {projects.map(p => (
                <li key={p.id} className="border rounded-lg hover:shadow-sm transition-shadow">
                  <Link href={`/spaces/${spaceId}/projects/${p.id}/materials`} className="block p-4">
                    <h3 className="text-lg font-semibold">{p.name}</h3>
                    {p.description && <p className="text-gray-600 text-sm mt-1">{p.description}</p>}
                    {p.learning_goal && (
                      <div className="mt-2 text-sm bg-blue-50 text-blue-800 p-2 rounded">
                        <span className="font-semibold">Goal:</span> {p.learning_goal}
                      </div>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
        
        <div>
          <div className="border p-4 rounded-lg shadow-sm bg-gray-50">
            <h2 className="text-xl font-semibold mb-4">Create a Project</h2>
            {createError && <div className="bg-red-100 text-red-700 p-2 mb-4 rounded text-sm">{createError}</div>}
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block mb-1 text-sm font-medium">Name</label>
                <input 
                  required 
                  value={name} 
                  onChange={e => setName(e.target.value)}
                  className="w-full border rounded px-3 py-2 text-sm"
                  placeholder="e.g. Midterm Prep"
                />
              </div>
              <div>
                <label className="block mb-1 text-sm font-medium">Description (Optional)</label>
                <textarea 
                  value={description} 
                  onChange={e => setDescription(e.target.value)}
                  className="w-full border rounded px-3 py-2 text-sm"
                  rows={2}
                />
              </div>
              <div>
                <label className="block mb-1 text-sm font-medium">Learning Goal (Optional)</label>
                <textarea 
                  value={learningGoal} 
                  onChange={e => setLearningGoal(e.target.value)}
                  className="w-full border rounded px-3 py-2 text-sm"
                  rows={2}
                  placeholder="What do you want to learn?"
                />
              </div>
              <Button type="submit" disabled={creating} className="w-full">
                {creating ? 'Creating...' : 'Create Project'}
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
