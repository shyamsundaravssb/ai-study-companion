'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface ProjectNavProps {
  spaceId: string;
  projectId: string;
}

export function ProjectNav({ spaceId, projectId }: ProjectNavProps) {
  const pathname = usePathname();
  
  return (
    <div className="mb-6">
      <Link href={`/spaces/${spaceId}`} className="text-sm text-blue-600 hover:underline">
        &larr; Back to Space
      </Link>
      <div className="flex space-x-6 mt-4 border-b">
        <Link 
          href={`/spaces/${spaceId}/projects/${projectId}/materials`}
          className={`text-sm font-medium pb-2 ${pathname.includes('/materials') ? 'text-blue-600 border-b-2 border-blue-600' : 'text-slate-600 hover:text-blue-600'}`}
        >
          Materials
        </Link>
        <Link 
          href={`/spaces/${spaceId}/projects/${projectId}/tutor`}
          className={`text-sm font-medium pb-2 ${pathname.includes('/tutor') ? 'text-blue-600 border-b-2 border-blue-600' : 'text-slate-600 hover:text-blue-600'}`}
        >
          Tutor
        </Link>
        <Link 
          href={`/spaces/${spaceId}/projects/${projectId}/quiz`}
          className={`text-sm font-medium pb-2 ${pathname.includes('/quiz') ? 'text-blue-600 border-b-2 border-blue-600' : 'text-slate-600 hover:text-blue-600'}`}
        >
          Quiz
        </Link>
      </div>
    </div>
  );
}
