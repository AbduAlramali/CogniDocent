import React, { useState } from "react";
import { Project } from "@/types";
import { documentsApi } from "@/api";
import { FileText, Trash2, Calendar, BookOpen } from "lucide-react";

interface ProjectCardProps {
  project: Project;
  onSelect: (project: Project) => void;
  onDelete: (projectId: string) => void;
  isDeleting?: boolean;
}

export const ProjectCard: React.FC<ProjectCardProps> = ({
  project,
  onSelect,
  onDelete,
  isDeleting,
}) => {
  const [thumbError, setThumbError] = useState(false);
  const thumbnailUrl = documentsApi.getThumbnailUrl(project.doc_id, "small");

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm(`Are you sure you want to delete "${project.title}"?`)) {
      onDelete(project.project_id);
    }
  };

  return (
    <div
      onClick={() => onSelect(project)}
      className="group relative flex flex-col bg-card text-card-foreground border border-border rounded-xl overflow-hidden shadow-sm hover:shadow-md hover:border-primary/50 transition-all cursor-pointer select-none"
    >
      {/* Thumbnail Aspect Container */}
      <div className="relative w-full h-48 bg-muted/40 flex items-center justify-center overflow-hidden border-b border-border">
        {!thumbError ? (
          <img
            src={thumbnailUrl}
            alt={project.title}
            onError={() => setThumbError(true)}
            className="w-full h-full object-cover object-top transition-transform duration-300 group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="flex flex-col items-center justify-center text-muted gap-2">
            <FileText className="w-12 h-12 text-primary/60" />
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              PDF Document
            </span>
          </div>
        )}

        {/* Hover Overlay Button */}
        <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary text-primary-foreground text-xs font-semibold shadow-lg">
            <BookOpen className="w-3.5 h-3.5" />
            Open Workspace
          </span>
        </div>

        {/* Top-Right Delete Action */}
        <button
          type="button"
          onClick={handleDelete}
          disabled={isDeleting}
          className="absolute top-2 right-2 p-1.5 rounded-lg bg-background/80 hover:bg-destructive hover:text-destructive-foreground text-muted-foreground backdrop-blur-sm transition-all opacity-0 group-hover:opacity-100 shadow-sm"
          title="Delete project"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Card Body */}
      <div className="p-4 flex-1 flex flex-col justify-between">
        <div>
          <h3
            className="font-semibold text-base text-foreground mb-1 line-clamp-1 group-hover:text-primary transition-colors"
            title={project.title}
          >
            {project.title}
          </h3>
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
            {project.description || "Research document ready for semantic exploration."}
          </p>
        </div>

        {/* Metadata Footer */}
        <div className="mt-4 pt-3 border-t border-border/60 flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5" />
            <span>
              {new Date(project.created_at).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
                year: "numeric",
              })}
            </span>
          </div>
          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
            ID: {project.project_id.slice(0, 6)}
          </span>
        </div>
      </div>
    </div>
  );
};
