import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import {
  buildGraph,
  getGraphStatus,
  getGraphData,
  getNodeDetail,
  deleteGraph,
  pollGraphStatus,
} from './knowledgeGraph'
import type {
  BuildGraphResponse,
  GraphStatusResponse,
  GraphData,
  ConceptNodeDetail,
} from '../types/knowledgeGraph'

// Mock global fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('knowledgeGraph API', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('buildGraph', () => {
    it('calls correct endpoint with POST method', async () => {
      const mockResponse: BuildGraphResponse = {
        jobId: 'job-123',
        textbookId: 'tb-1',
        status: 'pending',
        message: 'Graph build started',
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          job_id: 'job-123',
          textbook_id: 'tb-1',
          status: 'pending',
          message: 'Graph build started',
        }),
      })

      const result = await buildGraph('tb-1')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/knowledge-graph/tb-1/build'),
        expect.objectContaining({ method: 'POST' })
      )
      expect(result).toEqual(mockResponse)
    })

    it('throws on non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
      })

      await expect(buildGraph('tb-1')).rejects.toThrow('Failed to build graph: 400')
    })

    it('maps snake_case response to camelCase', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          job_id: 'job-456',
          textbook_id: 'tb-2',
          status: 'processing',
          message: 'Processing',
        }),
      })

      const result = await buildGraph('tb-2')

      expect(result.jobId).toBe('job-456')
      expect(result.textbookId).toBe('tb-2')
    })
  })

  describe('getGraphStatus', () => {
    it('calls correct endpoint with GET method', async () => {
      const mockResponse: GraphStatusResponse = {
        jobId: 'job-123',
        textbookId: 'tb-1',
        status: 'processing',
        progressPct: 50,
        totalChapters: 10,
        processedChapters: 5,
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          job_id: 'job-123',
          textbook_id: 'tb-1',
          status: 'processing',
          progress_pct: 50,
          total_chapters: 10,
          processed_chapters: 5,
        }),
      })

      const result = await getGraphStatus('tb-1')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/knowledge-graph/tb-1/status'),
        expect.objectContaining({ method: 'GET' })
      )
      expect(result).toEqual(mockResponse)
    })

    it('throws on non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      })

      await expect(getGraphStatus('tb-1')).rejects.toThrow('Failed to get graph status: 404')
    })

    it('maps snake_case response to camelCase', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          job_id: 'job-789',
          textbook_id: 'tb-3',
          status: 'completed',
          progress_pct: 100,
          total_chapters: 5,
          processed_chapters: 5,
        }),
      })

      const result = await getGraphStatus('tb-3')

      expect(result.progressPct).toBe(100)
      expect(result.totalChapters).toBe(5)
      expect(result.processedChapters).toBe(5)
    })
  })

  describe('getGraphData', () => {
    it('calls correct endpoint and returns graph data', async () => {
      const mockResponse: GraphData = {
        textbookId: 'tb-1',
        nodes: [
          {
            id: 'node-1',
            textbookId: 'tb-1',
            title: 'Theorem 1',
            nodeType: 'theorem',
            level: 'section',
            createdAt: '2024-01-01T00:00:00Z',
          },
        ],
        edges: [
          {
            id: 'edge-1',
            textbookId: 'tb-1',
            sourceNodeId: 'node-1',
            targetNodeId: 'node-2',
            relationshipType: 'derives_from',
            confidence: 0.95,
            createdAt: '2024-01-01T00:00:00Z',
          },
        ],
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          textbook_id: 'tb-1',
          nodes: [
            {
              id: 'node-1',
              textbook_id: 'tb-1',
              title: 'Theorem 1',
              node_type: 'theorem',
              level: 'section',
              created_at: '2024-01-01T00:00:00Z',
            },
          ],
          edges: [
            {
              id: 'edge-1',
              textbook_id: 'tb-1',
              source_node_id: 'node-1',
              target_node_id: 'node-2',
              relationship_type: 'derives_from',
              confidence: 0.95,
              created_at: '2024-01-01T00:00:00Z',
            },
          ],
        }),
      })

      const result = await getGraphData('tb-1')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/knowledge-graph/tb-1/graph'),
        expect.objectContaining({ method: 'GET' })
      )
      expect(result).toEqual(mockResponse)
    })

    it('throws on non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      })

      await expect(getGraphData('tb-1')).rejects.toThrow('Failed to get graph data: 500')
    })
  })

  describe('getNodeDetail', () => {
    it('calls correct endpoint with node ID', async () => {
      const mockResponse: ConceptNodeDetail = {
        node: {
          id: 'node-1',
          textbookId: 'tb-1',
          title: 'Theorem 1',
          nodeType: 'theorem',
          level: 'section',
          createdAt: '2024-01-01T00:00:00Z',
        },
        incomingEdges: [],
        outgoingEdges: [],
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          node: {
            id: 'node-1',
            textbook_id: 'tb-1',
            title: 'Theorem 1',
            node_type: 'theorem',
            level: 'section',
            created_at: '2024-01-01T00:00:00Z',
          },
          incoming_edges: [],
          outgoing_edges: [],
        }),
      })

      const result = await getNodeDetail('tb-1', 'node-1')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/knowledge-graph/tb-1/node/node-1'),
        expect.objectContaining({ method: 'GET' })
      )
      expect(result).toEqual(mockResponse)
    })

    it('throws on non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      })

      await expect(getNodeDetail('tb-1', 'node-1')).rejects.toThrow(
        'Failed to get node detail: 404'
      )
    })
  })

  describe('deleteGraph', () => {
    it('calls correct endpoint with DELETE method', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      })

      await deleteGraph('tb-1')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/knowledge-graph/tb-1'),
        expect.objectContaining({ method: 'DELETE' })
      )
    })

    it('throws on non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
      })

      await expect(deleteGraph('tb-1')).rejects.toThrow('Failed to delete graph: 403')
    })
  })

  describe('pollGraphStatus', () => {
    it('polls until status is completed', async () => {
      const onProgress = vi.fn()

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            job_id: 'job-1',
            textbook_id: 'tb-1',
            status: 'processing',
            progress_pct: 25,
            total_chapters: 10,
            processed_chapters: 2,
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            job_id: 'job-1',
            textbook_id: 'tb-1',
            status: 'processing',
            progress_pct: 50,
            total_chapters: 10,
            processed_chapters: 5,
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            job_id: 'job-1',
            textbook_id: 'tb-1',
            status: 'completed',
            progress_pct: 100,
            total_chapters: 10,
            processed_chapters: 10,
          }),
        })

      const result = await pollGraphStatus('tb-1', 10, onProgress)

      expect(result.status).toBe('completed')
      expect(onProgress).toHaveBeenCalledTimes(3)
      expect(mockFetch).toHaveBeenCalledTimes(3)
    })

    it('stops polling on failed status', async () => {
      const onProgress = vi.fn()

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            job_id: 'job-1',
            textbook_id: 'tb-1',
            status: 'processing',
            progress_pct: 50,
            total_chapters: 10,
            processed_chapters: 5,
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            job_id: 'job-1',
            textbook_id: 'tb-1',
            status: 'failed',
            progress_pct: 50,
            total_chapters: 10,
            processed_chapters: 5,
            error: 'Processing failed',
          }),
        })

      const result = await pollGraphStatus('tb-1', 10, onProgress)

      expect(result.status).toBe('failed')
      expect(result.error).toBe('Processing failed')
      expect(onProgress).toHaveBeenCalledTimes(2)
    })
  })
})
