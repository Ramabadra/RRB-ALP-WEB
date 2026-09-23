"use client";

import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { UploadCloud, CheckCircle2, AlertCircle, FileText, Loader2, ArrowRight } from "lucide-react";
import { pdfsApi } from "@/lib/api/services";
import { PDFProcessingJob } from "@/types";
import Link from "next/link";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [examName, setExamName] = useState("");
  const [examYear, setExamYear] = useState("");
  const [uploading, setUploading] = useState(false);
  const [currentJob, setCurrentJob] = useState<PDFProcessingJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Clean up polling interval on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (!selected.name.endsWith('.pdf')) {
        setError("Only PDF files are supported.");
        return;
      }
      setFile(selected);
      setError(null);
    }
  };

  const startStatusPolling = (jobId: string) => {
    if (pollingRef.current) clearInterval(pollingRef.current);

    pollingRef.current = setInterval(async () => {
      try {
        const statusData = await pdfsApi.getStatus(jobId);
        setCurrentJob(statusData);

        if (statusData.status === 'COMPLETED') {
          if (pollingRef.current) clearInterval(pollingRef.current);
          setUploading(false);
        } else if (statusData.status === 'FAILED') {
          if (pollingRef.current) clearInterval(pollingRef.current);
          setUploading(false);
          setError(statusData.error || statusData.error_message || "PDF extraction failed. Please ensure the PDF is valid.");
        }
      } catch (err: any) {
        console.error("Polling status error", err);
      }
    }, 2500);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setCurrentJob(null);

    try {
      const uploadRes = await pdfsApi.upload(file, {
        examName: examName || file.name.replace('.pdf', ''),
        examYear: examYear || undefined,
      });

      setCurrentJob({
        id: uploadRes.jobId || uploadRes.documentId,
        jobId: uploadRes.jobId,
        documentId: uploadRes.documentId,
        status: uploadRes.status || 'PROCESSING',
        progress: uploadRes.progress || 10,
      });

      startStatusPolling(uploadRes.jobId || uploadRes.documentId);
    } catch (err: any) {
      console.error(err);
      setError(err?.message || "Failed to upload file. Please check backend connection.");
      setUploading(false);
    }
  };

  return (
    <div className="p-6 md:p-8 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Upload PYQ Document</h1>
        <p className="text-muted-foreground mt-1">
          Upload Previous Year Question papers to extract and add them to your question bank.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>File Upload</CardTitle>
          <CardDescription>Select an official RRB ALP question paper PDF</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {error && (
            <div className="p-4 rounded-lg bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-400 text-sm border border-red-200 dark:border-red-900 flex items-start gap-2">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">Exam Title / Shift (Optional)</label>
              <input
                type="text"
                placeholder="e.g. RRB ALP 2018 Shift 1"
                value={examName}
                onChange={(e) => setExamName(e.target.value)}
                disabled={uploading}
                className="w-full px-3 py-2 border rounded-md text-sm bg-background border-input"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">Exam Year (Optional)</label>
              <input
                type="text"
                placeholder="e.g. 2018"
                value={examYear}
                onChange={(e) => setExamYear(e.target.value)}
                disabled={uploading}
                className="w-full px-3 py-2 border rounded-md text-sm bg-background border-input"
              />
            </div>
          </div>

          <div className="border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-xl p-8 text-center hover:border-indigo-400 dark:hover:border-indigo-700 transition-colors bg-slate-50/50 dark:bg-slate-900/50">
            <input 
              type="file" 
              accept=".pdf" 
              id="file-upload" 
              className="sr-only" 
              onChange={handleFileChange}
              disabled={uploading}
            />
            <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center justify-center">
              <UploadCloud className="w-12 h-12 text-indigo-500 mb-4" />
              <span className="text-base font-medium text-foreground">
                {file ? file.name : "Click to browse or drag and drop"}
              </span>
              <span className="text-xs text-muted-foreground mt-1">
                Supported format: PDF up to 25MB
              </span>
            </label>
          </div>

          {currentJob && (
            <div className="p-5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 space-y-3">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 font-medium">
                  {currentJob.status === 'COMPLETED' ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                  ) : currentJob.status === 'FAILED' ? (
                    <AlertCircle className="w-5 h-5 text-red-500" />
                  ) : (
                    <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
                  )}
                  <span className="capitalize">{currentJob.status.toLowerCase()}</span>
                  {currentJob.current_stage && (
                    <span className="text-xs text-muted-foreground font-normal">
                      • {currentJob.current_stage}
                    </span>
                  )}
                </div>
                <span className="font-semibold">{Math.round(currentJob.progress || 0)}%</span>
              </div>
              
              <div className="w-full h-2 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className={`h-full transition-all duration-300 ${currentJob.status === 'FAILED' ? 'bg-red-500' : currentJob.status === 'COMPLETED' ? 'bg-emerald-500' : 'bg-indigo-600'}`}
                  style={{ width: `${Math.max(5, currentJob.progress || 0)}%` }}
                />
              </div>

              {currentJob.status === 'COMPLETED' && (
                <div className="pt-2 flex justify-end gap-3">
                  <Button asChild className="glass-button">
                    <Link href="/question-bank">
                      View Question Bank <ArrowRight className="w-4 h-4 ml-1" />
                    </Link>
                  </Button>
                </div>
              )}
            </div>
          )}

          <Button 
            onClick={handleUpload} 
            disabled={!file || uploading} 
            className="w-full glass-button h-11"
          >
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Processing with FastAPI Server...
              </>
            ) : (
              'Upload and Process PDF'
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
