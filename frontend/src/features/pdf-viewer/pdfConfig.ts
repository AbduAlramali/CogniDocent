import { pdfjs } from "react-pdf";

// Configure PDF.js worker using unpkg or local worker bundle
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

export { pdfjs };
