// Pipeline status types
export type PipelineStatus = 'uploaded' | 'toc_extracted' | 'awaiting_verification' | 'extracting' | 'partially_extracted' | 'fully_extracted' | 'error';

// Chapter extraction status types
export type ExtractionStatus = 'pending' | 'selected' | 'extracting' | 'extracted' | 'deferred' | 'error';

// Content type enumeration
export type ContentType = 'table' | 'figure' | 'equation' | 'text';

// Material topic within a summary
export interface MaterialTopic {
  title: string;
  description: string;
  source_range?: string; // e.g., "slides 1-5"
}

// Material summary with extracted topics
export interface MaterialSummary {
  id: string;
  material_id: string;
  course_id: string;
  topics: MaterialTopic[];
  raw_summary?: string;
  created_at?: string;
}

// Relevance matching result for a chapter
export interface RelevanceResult {
  chapter_id: string;
  chapter_title: string;
  relevance_score: number; // 0.0-1.0
  matched_topics: string[];
  reasoning?: string;
}

// Chapter with extraction and relevance status
export interface ChapterWithStatus {
  id: string;
  title: string;
  chapter_number: number;
  page_start: number;
  page_end: number;
  extraction_status: ExtractionStatus;
  relevance_score?: number;
  matched_topics?: string[];
}

// Textbook pipeline status overview
export interface TextbookPipelineStatus {
  pipeline_status: PipelineStatus;
  chapters: ChapterWithStatus[];
}
