import { apiClient } from "./client";
import { Project, ProjectCreatedResponse } from "../types";

export interface CreateProjectParams {
  file: File;
  title?: string;
}

export const projectsApi = {
  async listProjects(): Promise<Project[]> {
    const response = await apiClient.get<Project[]>("/projects");
    return response.data;
  },

  async getProject(projectId: string): Promise<Project> {
    const response = await apiClient.get<Project>(`/projects/${projectId}`);
    return response.data;
  },

  async createProject(params: CreateProjectParams): Promise<ProjectCreatedResponse> {
    const formData = new FormData();
    formData.append("file", params.file);
    if (params.title && params.title.trim()) {
      formData.append("title", params.title.trim());
    }

    const response = await apiClient.post<ProjectCreatedResponse>("/projects", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },

  async deleteProject(projectId: string): Promise<void> {
    await apiClient.delete(`/projects/${projectId}`);
  },
};
