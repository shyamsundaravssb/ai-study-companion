"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { quizApi } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { ProjectNav } from "@/components/ProjectNav";

export default function QuizPage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const spaceId = params.spaceId as string;
  const [assessment, setAssessment] = useState<any>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleGenerate = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await quizApi.generateQuiz(projectId);
      setAssessment(data);
      setAnswers({});
    } catch (err: any) {
      setError(err.message || "Failed to generate quiz.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError("");
    const formattedAnswers = Object.entries(answers).map(([question_id, answer]) => ({
      question_id,
      answer
    }));

    try {
      const res = await quizApi.submitAssessment(projectId, assessment.id, formattedAnswers);
      setAssessment(res.assessment);
    } catch (err: any) {
      setError(err.message || "Failed to submit assessment.");
    } finally {
      setLoading(false);
    }
  };

  if (!assessment) {
    return (
      <div className="p-8 max-w-2xl mx-auto text-center mt-6">
        <div className="text-left"><ProjectNav spaceId={spaceId} projectId={projectId} /></div>
        <h1 className="text-3xl font-bold mb-4">Project Assessment</h1>
        <p className="text-muted-foreground mb-8">Test your knowledge on the concepts in this project.</p>
        <Button onClick={handleGenerate} disabled={loading} size="lg">
          {loading ? "Generating Quiz..." : "Generate Adaptive Quiz"}
        </Button>
        {error && <p className="text-red-500 mt-4">{error}</p>}
      </div>
    );
  }

  const isCompleted = assessment.status === "completed";

  return (
    <div className="p-8 max-w-3xl mx-auto pb-24">
      <ProjectNav spaceId={spaceId} projectId={projectId} />
      <h1 className="text-2xl font-bold mb-8">Quiz</h1>
      {error && <div className="bg-red-100 text-red-800 p-4 rounded mb-4">{error}</div>}
      
      <div className="space-y-8">
        {assessment.questions.map((q: any, i: number) => (
          <div key={q.id} className="p-6 border rounded-lg bg-card">
            <p className="font-medium mb-4">{i + 1}. {q.question_text}</p>
            
            {q.type === "mcq" ? (
              <div className="space-y-2">
                {q.options?.map((opt: any, idx: number) => (
                  <label key={idx} className="flex items-center space-x-2">
                    <input
                      type="radio"
                      name={`q-${q.id}`}
                      value={opt.text}
                      checked={answers[q.id] === opt.text || q.user_answer === opt.text}
                      onChange={(e) => !isCompleted && setAnswers({...answers, [q.id]: e.target.value})}
                      disabled={isCompleted}
                      className="w-4 h-4"
                    />
                    <span>{opt.text}</span>
                  </label>
                ))}
              </div>
            ) : (
              <textarea
                className="w-full p-3 border rounded-md"
                rows={4}
                placeholder="Write your answer..."
                value={answers[q.id] || q.user_answer || ""}
                onChange={(e) => !isCompleted && setAnswers({...answers, [q.id]: e.target.value})}
                disabled={isCompleted}
              />
            )}

            {isCompleted && (
              <div className="mt-4 p-4 rounded bg-muted/50 border">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-semibold text-sm">Feedback</span>
                  <span className={`text-sm font-bold ${q.score >= 0.8 ? 'text-green-600' : q.score >= 0.5 ? 'text-yellow-600' : 'text-red-600'}`}>
                    Score: {q.score !== null ? (q.score * 100).toFixed(0) + '%' : 'N/A'}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">{q.feedback}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {!isCompleted && (
        <div className="mt-8 flex justify-end">
          <Button onClick={handleSubmit} disabled={loading} size="lg">
            {loading ? "Submitting..." : "Submit Quiz"}
          </Button>
        </div>
      )}
    </div>
  );
}
