import React, { useState } from "react";
import { Project } from "@/types";
import { ProjectCard } from "./ProjectCard";
import { Plus, Search, FolderPlus } from "lucide-react";

interface ProjectGridProps {
  projects: Project[];
  isLoading: boolean;
  onSelectProject: (project: Project) => void;
  onDeleteProject: (projectId: string) => void;
  onOpenCreateModal: () => void;
}

export const ProjectGrid: React.FC<ProjectGridProps> = ({
  projects,
  isLoading,
  onSelectProject,
  onDeleteProject,
  onOpenCreateModal,
}) => {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredProjects = projects.filter((p) =>
    p.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Search & Actions Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search projects by title..."
            className="w-full pl-10 pr-4 py-2 text-sm bg-card text-foreground border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all"
          />
        </div>

        <button
          type="button"
          onClick={onOpenCreateModal}
          className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-semibold rounded-xl bg-primary text-primary-foreground hover:bg-primary/95 shadow-sm transition-all whitespace-nowrap"
        >
          <Plus className="w-4 h-4" />
          <span>New Project</span>
        </button>
      </div>

      {/* Loading Skeletons */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((n) => (
            <div
              key={n}
              className="bg-card border border-border rounded-xl overflow-hidden animate-pulse flex flex-col h-72"
            >
              <div className="h-44 bg-muted" />
              <div className="p-4 space-y-3 flex-1">
                <div className="h-4 bg-muted rounded w-3/4" />
                <div className="h-3 bg-muted rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      ) : filteredProjects.length > 0 ? (
        /* Grid */
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {filteredProjects.map((project) => (
            <ProjectCard
              key={project.project_id}
              project={project}
              onSelect={onSelectProject}
              onDelete={onDeleteProject}
            />
          ))}
        </div>
      ) : (
        /* Empty State */
        <div className="text-center py-16 px-4 border border-dashed border-border rounded-2xl bg-card/50">
          <div className="w-14 h-14 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mx-auto mb-4">
            <FolderPlus className="w-7 h-7" />
          </div>
          <h3 className="text-lg font-bold text-foreground">
            {searchQuery ? "No matching projects found" : "No projects created yet"}
          </h3>
          <p className="text-sm text-muted-foreground max-w-sm mx-auto mt-1.5 mb-6">
            {searchQuery
              ? `Try searching for another keyword or clear your query.`
              : `Upload your first PDF document to start researching with AI.`}
          </p>
          <button
            type="button"
            onClick={onOpenCreateModal}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary/95 shadow-sm transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Upload Document</span>
          </button>
        </div>
      )}
    </div>
  );
};
