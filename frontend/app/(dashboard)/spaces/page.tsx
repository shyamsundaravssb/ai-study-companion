'use client';
import { useEffect, useState } from 'react';
import { fetchApi } from '@/lib/api-client';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function SpacesPage() {
  const [spaces, setSpaces] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const loadSpaces = () => {
    setLoading(true);
    fetchApi('/spaces')
      .then(data => {
        setSpaces(data);
        setError(null);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadSpaces();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);
    try {
      await fetchApi('/spaces/', {
        method: 'POST',
        body: JSON.stringify({ name, description: description || null })
      });
      setName('');
      setDescription('');
      loadSpaces();
    } catch (err: any) {
      setCreateError(err.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Your Spaces</h1>
      
      {error && <div className="bg-red-100 text-red-700 p-4 mb-6 rounded">{error}</div>}
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2">
          {loading ? (
            <div className="text-gray-500">Loading spaces...</div>
          ) : spaces.length === 0 ? (
            <div className="p-8 border border-dashed rounded-lg text-center text-gray-500">
              You don't have any Spaces yet.
            </div>
          ) : (
            <ul className="space-y-3">
              {spaces.map(s => (
                <li key={s.id} className="border p-4 rounded-lg hover:shadow-sm transition-shadow">
                  <Link href={`/spaces/${s.id}`} className="block">
                    <h2 className="text-xl font-semibold text-blue-600 hover:underline">{s.name}</h2>
                    {s.description && <p className="text-gray-600 mt-1 text-sm">{s.description}</p>}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
        
        <div>
          <div className="border p-4 rounded-lg shadow-sm bg-gray-50">
            <h2 className="text-xl font-semibold mb-4">Create a Space</h2>
            {createError && <div className="bg-red-100 text-red-700 p-2 mb-4 rounded text-sm">{createError}</div>}
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block mb-1 text-sm font-medium">Name</label>
                <input 
                  required 
                  value={name} 
                  onChange={e => setName(e.target.value)}
                  className="w-full border rounded px-3 py-2 text-sm"
                  placeholder="e.g. Physics 101"
                />
              </div>
              <div>
                <label className="block mb-1 text-sm font-medium">Description (Optional)</label>
                <textarea 
                  value={description} 
                  onChange={e => setDescription(e.target.value)}
                  className="w-full border rounded px-3 py-2 text-sm"
                  rows={3}
                />
              </div>
              <Button type="submit" disabled={creating} className="w-full">
                {creating ? 'Creating...' : 'Create Space'}
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
