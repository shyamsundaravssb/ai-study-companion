'use client';

import { useEffect, useState, use, useRef } from 'react';
import { fetchApi } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { ProjectNav } from '@/components/ProjectNav';

export default function MaterialsPage({ params }: { params: Promise<{ spaceId: string, projectId: string }> }) {
  const { spaceId, projectId } = use(params);
  
  const [project, setProject] = useState<any>(null);
  const [materials, setMaterials] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadData = async () => {
    try {
      const [projData, matsData] = await Promise.all([
        fetchApi(`/projects/${projectId}`, { cache: 'no-store' }),
        fetchApi(`/projects/${projectId}/materials`, { cache: 'no-store' })
      ]);
      setProject(projData);
      setMaterials(matsData);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadMaterials = async () => {
    try {
      const matsData = await fetchApi(`/projects/${projectId}/materials`, {
        cache: 'no-store',
      });
      setMaterials(matsData);
    } catch (err) {
      console.error("Failed to refresh materials:", err);
    }
  };

  useEffect(() => {
    loadData();
  }, [projectId]);

  // Polling effect
  useEffect(() => {
    const hasPending = materials.some(m => m.status === 'queued' || m.status === 'processing');
    
    if (!hasPending) {
      console.log("No pending materials, skipping/stopping poll.");
      return;
    }

    console.log("Pending materials found, starting 3s polling interval...");

    const intervalId = setInterval(() => {
      console.log("Polling tick: fetching materials...");
      loadMaterials();
    }, 3000);

    return () => {
      console.log("Clearing polling interval");
      clearInterval(intervalId);
    };
  }, [materials, projectId]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    } else {
      setFile(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      await fetchApi(`/projects/${projectId}/materials`, {
        method: 'POST',
        body: formData,
      });
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      loadMaterials();
    } catch (err: any) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  };
  
  const getStatusBadge = (status: string) => {
    switch(status) {
      case 'ready':
        return <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded-full">Ready</span>;
      case 'failed':
        return <span className="px-2 py-1 bg-red-100 text-red-800 text-xs font-semibold rounded-full">Failed</span>;
      case 'processing':
        return <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded-full animate-pulse">Processing</span>;
      case 'queued':
      default:
        return <span className="px-2 py-1 bg-gray-100 text-gray-800 text-xs font-semibold rounded-full">Queued</span>;
    }
  };

  if (loading) return <div className="p-6 text-gray-500">Loading materials...</div>;
  if (error) return <div className="p-6 text-red-600">Error: {error}</div>;
  if (!project) return <div className="p-6">Project not found</div>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-6">
        <ProjectNav spaceId={spaceId} projectId={projectId} />
        <h1 className="text-3xl font-bold mt-2">{project.name}</h1>
        <p className="text-gray-600 mt-1">Manage learning materials for this project.</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2">
          <h2 className="text-2xl font-semibold mb-4">Materials</h2>
          {materials.length === 0 ? (
            <div className="p-8 border border-dashed rounded-lg text-center text-gray-500">
              No materials uploaded yet. Upload a PDF to get started!
            </div>
          ) : (
            <ul className="space-y-3">
              {materials.map(m => (
                <li key={m.id} className="border p-4 rounded-lg flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900 truncate max-w-sm" title={m.filename}>
                      {m.filename}
                    </h3>
                    <p className="text-xs text-gray-500 mt-1">
                      Uploaded: {new Date(m.uploaded_at).toLocaleString()}
                    </p>
                  </div>
                  <div>
                    {getStatusBadge(m.status)}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
        
        <div>
          <div className="border p-4 rounded-lg shadow-sm bg-gray-50">
            <h2 className="text-xl font-semibold mb-4">Upload PDF</h2>
            {uploadError && (
              <div className="bg-red-100 text-red-700 p-2 mb-4 rounded text-sm break-words">
                {uploadError}
              </div>
            )}
            <form onSubmit={handleUpload} className="space-y-4">
              <div>
                <label className="block mb-1 text-sm font-medium">File</label>
                <input 
                  type="file"
                  accept="application/pdf"
                  onChange={handleFileChange}
                  ref={fileInputRef}
                  className="w-full border rounded px-3 py-2 text-sm bg-white"
                  disabled={uploading}
                />
              </div>
              <Button type="submit" disabled={!file || uploading} className="w-full">
                {uploading ? 'Uploading...' : 'Upload Material'}
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
