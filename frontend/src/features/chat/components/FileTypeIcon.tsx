import React from "react";
import {
  FileText,
  FileCode,
  FileSpreadsheet,
  FileArchive,
  FileImage,
  File,
} from "lucide-react";

interface FileTypeIconProps {
  fileName?: string;
  contentType?: string;
  className?: string;
}

export const FileTypeIcon: React.FC<FileTypeIconProps> = ({
  fileName = "",
  contentType = "",
  className = "w-4 h-4",
}) => {
  const lowerName = fileName.toLowerCase();
  const lowerType = contentType.toLowerCase();

  // 1. PDF
  if (lowerType === "application/pdf" || lowerName.endsWith(".pdf")) {
    return (
      <div className="relative flex items-center justify-center">
        <FileText className={`${className} text-red-500`} />
        <span className="absolute -bottom-1 -right-1 text-[8px] font-black leading-none px-0.5 rounded bg-red-600 text-white select-none">
          PDF
        </span>
      </div>
    );
  }

  // 2. Images
  if (lowerType.startsWith("image/") || /\.(png|jpe?g|gif|webp|svg|bmp)$/i.test(lowerName)) {
    return <FileImage className={`${className} text-sky-500`} />;
  }

  // 3. Spreadsheets & Tables
  if (
    lowerType.includes("spreadsheet") ||
    lowerType.includes("excel") ||
    lowerType === "text/csv" ||
    /\.(xlsx?|csv|tsv)$/i.test(lowerName)
  ) {
    return <FileSpreadsheet className={`${className} text-emerald-500`} />;
  }

  // 4. Code & Structured Data
  if (
    lowerType.includes("json") ||
    lowerType.includes("javascript") ||
    lowerType.includes("typescript") ||
    lowerType.includes("python") ||
    /\.(json|js|jsx|ts|tsx|py|html|css|yaml|yml)$/i.test(lowerName)
  ) {
    return <FileCode className={`${className} text-indigo-500`} />;
  }

  // 5. Archives
  if (
    lowerType.includes("zip") ||
    lowerType.includes("tar") ||
    lowerType.includes("compressed") ||
    /\.(zip|tar|gz|rar|7z)$/i.test(lowerName)
  ) {
    return <FileArchive className={`${className} text-violet-500`} />;
  }

  // 6. Word / Rich Text
  if (
    lowerType.includes("word") ||
    lowerType.includes("officedocument") ||
    /\.(docx?|rtf|odt)$/i.test(lowerName)
  ) {
    return <FileText className={`${className} text-blue-500`} />;
  }

  // 7. Plain Text & Markdown
  if (lowerType.startsWith("text/") || /\.(txt|md|log)$/i.test(lowerName)) {
    return <FileText className={`${className} text-amber-500`} />;
  }

  // Default File Icon
  return <File className={`${className} text-muted-foreground`} />;
};
