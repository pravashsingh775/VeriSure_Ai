import axios from 'axios';
import type {
  AdminAnalytics,
  AuthResponse,
  BrandAnalytics,
  ModelEntity,
  ReferenceImage,
  ScanDetail,
  ScanSummary,
  SuspiciousCase,
  User,
} from '../types';

const API_BASE = '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach Authorization header if token exists
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('verisure_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authApi = {
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const res = await apiClient.post<AuthResponse>('/auth/login', { email, password });
    localStorage.setItem('verisure_token', res.data.access_token);
    localStorage.setItem('verisure_user', JSON.stringify(res.data.user));
    return res.data;
  },
  register: async (data: {
    email: string;
    password: string;
    full_name: string;
    role_name?: string;
  }): Promise<User> => {
    const res = await apiClient.post<User>('/auth/register', data);
    return res.data;
  },
  getCurrentUser: async (): Promise<User> => {
    const res = await apiClient.get<User>('/auth/me');
    return res.data;
  },
  logout: () => {
    localStorage.removeItem('verisure_token');
    localStorage.removeItem('verisure_user');
  },
};

export const scanApi = {
  uploadScan: async (file: File, viewType = 'FRONT'): Promise<ScanDetail> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('view_type', viewType);

    const res = await apiClient.post<ScanDetail>('/scans/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },
  getScanDetail: async (scanId: string): Promise<ScanDetail> => {
    const res = await apiClient.get<ScanDetail>(`/scans/${scanId}`);
    return res.data;
  },
  getMyHistory: async (): Promise<ScanSummary[]> => {
    const res = await apiClient.get<ScanSummary[]>('/scans/history/me');
    return res.data;
  },
  getReportDownloadUrl: (scanId: string) => {
    const token = localStorage.getItem('verisure_token');
    return `/api/v1/scans/${scanId}/report${token ? `?token=${encodeURIComponent(token)}` : ''}`;
  },
  downloadReport: async (scanId: string): Promise<void> => {
    const res = await apiClient.get(`/scans/${scanId}/report`, {
      responseType: 'blob',
    });
    const blob = new Blob([res.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `VeriSure_Risk_Assessment_${scanId.slice(0, 8)}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
};

export const caseApi = {
  listCases: async (status?: string): Promise<SuspiciousCase[]> => {
    const params = status ? { status } : {};
    const res = await apiClient.get<SuspiciousCase[]>('/cases', { params });
    return res.data;
  },
  reviewCase: async (caseId: string, newStatus: string, comments: string): Promise<SuspiciousCase> => {
    const res = await apiClient.post<SuspiciousCase>(`/cases/${caseId}/review`, {
      new_status: newStatus,
      comments,
    });
    return res.data;
  },
};

export const modelApi = {
  listModels: async (): Promise<ModelEntity[]> => {
    const res = await apiClient.get<ModelEntity[]>('/models');
    return res.data;
  },
  runEvaluation: async (versionId: string): Promise<any> => {
    const res = await apiClient.post(`/models/versions/${versionId}/evaluate`, {
      simulate_perturbations: true,
    });
    return res.data;
  },
};

export const analyticsApi = {
  getAdminAnalytics: async (): Promise<AdminAnalytics> => {
    const res = await apiClient.get<AdminAnalytics>('/analytics/admin');
    return res.data;
  },
};

export const brandApi = {
  getPackagingVersions: async () => {
    const res = await apiClient.get('/packaging-versions');
    return res.data;
  },
  getProducts: async () => {
    const res = await apiClient.get('/products');
    return res.data;
  },
  getReferences: async (packagingVersionId?: string): Promise<ReferenceImage[]> => {
    const params = packagingVersionId ? { packaging_version_id: packagingVersionId } : {};
    const res = await apiClient.get<ReferenceImage[]>('/references', { params });
    return res.data;
  },
  getBrandAnalytics: async (brandId = 'AMUL'): Promise<BrandAnalytics> => {
    const res = await apiClient.get<BrandAnalytics>(`/analytics/brand/${brandId}`);
    return res.data;
  },
};


