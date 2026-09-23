import { fetchApi, USE_MOCKS } from '../client';
import { PDFDocument, PDFProcessingJob, PDFUploadResponse, Question } from '@/types';
import { normalizeQuestion } from './questions';

export const pdfsApi = {
  upload: async (
    file: File, 
    metadata?: { examName?: string; examYear?: string; examShift?: string }
  ): Promise<PDFUploadResponse> => {
    if (USE_MOCKS) {
      return {
        jobId: 'job-' + Date.now(),
        documentId: 'doc-' + Date.now(),
        status: 'QUEUED',
        progress: 10,
      };
    }

    const formData = new FormData();
    formData.append('file', file);
    if (metadata?.examName) {
      formData.append('exam_name', metadata.examName);
      formData.append('examName', metadata.examName);
    }
    if (metadata?.examYear) {
      formData.append('exam_year', metadata.examYear);
    }
    if (metadata?.examShift) {
      formData.append('exam_shift', metadata.examShift);
    }

    const res = await fetchApi<any>('/api/pdfs/upload', {
      method: 'POST',
      body: formData,
    });

    return {
      jobId: res.jobId || res.job_id || res.id,
      documentId: res.documentId || res.document_id || res.id,
      status: res.status || 'QUEUED',
      progress: res.progress ?? res.progress_pct ?? 0,
    };
  },

  list: async (): Promise<PDFDocument[]> => {
    if (USE_MOCKS) return [];
    try {
      const data = await fetchApi<any>('/api/pdfs');
      if (Array.isArray(data)) return data;
      if (data && Array.isArray(data.items)) return data.items;
      return [];
    } catch {
      return [];
    }
  },

  getById: async (id: string): Promise<PDFDocument> => {
    return fetchApi<PDFDocument>(`/api/pdfs/${id}`);
  },

  getStatus: async (id: string): Promise<PDFProcessingJob> => {
    if (USE_MOCKS) {
      return {
        id,
        status: 'COMPLETED',
        progress: 100,
      };
    }

    const res = await fetchApi<any>(`/api/pdfs/${id}/status`);
    return {
      id: res.id || res.jobId || res.job_id || id,
      jobId: res.jobId || res.job_id,
      documentId: res.documentId || res.document_id,
      status: res.status,
      progress: res.progress ?? res.progress_pct ?? 0,
      progress_pct: res.progress_pct ?? res.progress,
      current_stage: res.current_stage || res.currentStage,
      error: res.error || res.error_message,
      error_message: res.error_message || res.error,
      message: res.message,
    };
  },

  getQuestions: async (documentId: string): Promise<Question[]> => {
    try {
      const res = await fetchApi<any>(`/api/pdfs/${documentId}/questions`);
      let list: any[] = [];
      if (Array.isArray(res)) list = res;
      else if (res && Array.isArray(res.items)) list = res.items;
      return list.map(normalizeQuestion);
    } catch {
      return [];
    }
  },
};
