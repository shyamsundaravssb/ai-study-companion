import { supabase } from './auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchApi(endpoint: string, options: RequestInit = {}) {
  const { data: { session } } = await supabase.auth.getSession();
  
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  
  if (session?.access_token) {
    headers.set('Authorization', `Bearer ${session.access_token}`);
  }
  
  const response = await fetch(`${API_URL}/api/v1${endpoint}`, {
    ...options,
    headers,
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  if (response.status !== 204) {
    return response.json();
  }
  return null;
}

export const quizApi = {
  generateQuiz: (projectId: string) => 
    fetchApi(`/projects/${projectId}/quiz/generate`, { method: 'POST' }),
  getAssessment: (projectId: string, assessmentId: string) =>
    fetchApi(`/projects/${projectId}/assessments/${assessmentId}`),
  submitAssessment: (projectId: string, assessmentId: string, answers: any) =>
    fetchApi(`/projects/${projectId}/assessments/${assessmentId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ answers })
    })
};
