import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useWorkspaceStore } from "@/shared/store/useWorkspaceStore";
import { projectsApi, documentsApi } from "@/api";
import { Project, ProjectCreatedResponse } from "@/types";
import { ProjectGrid, CreateProjectModal } from "@/features/dashboard";
import { DocumentViewer } from "@/features/pdf-viewer";
import { ChatContainer } from "@/features/chat";
import { SettingsDrawer } from "@/features/settings";
import { BookOpen, Settings, LayoutGrid, Sparkles } from "lucide-react";

export const App: React.FC = () => {
  const queryClient = useQueryClient();

  const activeProjectId = useWorkspaceStore((state) => state.activeProjectId);
  const setActiveProjectId = useWorkspaceStore((state) => state.setActiveProjectId);
  const activeProject = useWorkspaceStore((state) => state.activeProject);
  const setActiveProject = useWorkspaceStore((state) => state.setActiveProject);
  const isSettingsOpen = useWorkspaceStore((state) => state.isSettingsOpen);
  const setIsSettingsOpen = useWorkspaceStore((state) => state.setIsSettingsOpen);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // 1. Fetch all projects
  const { data: projects = [], isLoading: isLoadingProjects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => projectsApi.listProjects(),
  });

  // 2. Delete project mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => projectsApi.deleteProject(id),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      if (activeProjectId === deletedId) {
        setActiveProject(null);
      }
    },
  });

  const handleSelectProject = (project: Project) => {
    setActiveProject(project);
  };

  const handleProjectCreated = async (created: ProjectCreatedResponse) => {
    await queryClient.invalidateQueries({ queryKey: ["projects"] });
    try {
      const fullProject = await projectsApi.getProject(created.project_id);
      setActiveProject(fullProject);
    } catch {
      setActiveProjectId(created.project_id);
    }
  };

  const currentProject =
    activeProject || projects.find((p) => p.project_id === activeProjectId);

  return (
    <div className="flex flex-col h-screen bg-background text-foreground font-sans overflow-hidden">
      {/* Top Navbar Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-card shadow-xs z-20 shrink-0 select-none">
        <div className="flex items-center space-x-4">
          <button
            type="button"
            onClick={() => setActiveProject(null)}
            className="text-lg font-extrabold cursor-pointer hover:opacity-85 tracking-tight flex items-center gap-2.5 transition-opacity"
          >
            <div className="w-8 h-8 rounded-xl bg-primary text-primary-foreground flex items-center justify-center shadow-xs">
              <Sparkles className="w-4 h-4" />
            </div>
            <span>CogniDocent</span>
          </button>

          {currentProject && (
            <div className="hidden sm:flex items-center gap-2 pl-3 border-l border-border text-xs">
              <span className="px-2.5 py-1 rounded-full bg-primary/10 text-primary font-medium flex items-center gap-1.5 truncate max-w-xs">
                <BookOpen className="w-3.5 h-3.5 shrink-0" />
                <span className="truncate">{currentProject.title}</span>
              </span>
            </div>
          )}
        </div>

        <div className="flex items-center space-x-2">
          {activeProjectId && (
            <button
              type="button"
              onClick={() => setActiveProject(null)}
              className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 border border-border rounded-xl hover:bg-muted font-medium transition-all"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span>Projects Grid</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => setIsSettingsOpen(true)}
            className="inline-flex items-center gap-1.5 text-xs px-3.5 py-1.5 rounded-xl border border-border hover:bg-muted font-medium transition-all"
          >
            <Settings className="w-3.5 h-3.5" />
            <span>Settings</span>
          </button>
        </div>
      </header>

      {/* Main Container Layout */}
      <main className="flex-1 overflow-hidden">
        {currentProject ? (
          // Split-Screen Workspace Viewer: PDF on Left (55%), Chats on Right (45%)
          <div className="flex h-full w-full">
            <div className="w-[55%] h-full">
              <DocumentViewer
                documentUrl={documentsApi.getDocumentFileUrl(currentProject.doc_id)}
                docId={currentProject.doc_id}
              />
            </div>
            <div className="w-[45%] h-full border-l border-border">
              <ChatContainer />
            </div>
          </div>
        ) : (
          // Homepage: Landing Project Grid Dashboard
          <div className="max-w-7xl mx-auto px-6 py-8 h-full overflow-y-auto space-y-8">
            <div className="text-center py-6 max-w-2xl mx-auto space-y-3">
              <h2 className="text-4xl font-extrabold tracking-tight">
                AI Document Research Assistant
              </h2>
              <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
                Upload research papers, technical manuals, and financial reports. Query with multimodal LLMs, snip diagrams, and navigate verified citations in real time.
              </p>
            </div>

            {/* Project Grid */}
            <ProjectGrid
              projects={projects}
              isLoading={isLoadingProjects}
              onSelectProject={handleSelectProject}
              onDeleteProject={(id) => deleteMutation.mutate(id)}
              onOpenCreateModal={() => setIsCreateModalOpen(true)}
            />
          </div>
        )}
      </main>

      {/* Project Creation Modal */}
      <CreateProjectModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handleProjectCreated}
      />

      {/* Provider API Key Settings Drawer */}
      <SettingsDrawer
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
  );
};

export default App;
