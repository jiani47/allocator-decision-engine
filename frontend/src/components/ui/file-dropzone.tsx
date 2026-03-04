import { useState, useCallback } from "react"
import { useDropzone } from "react-dropzone"
import { Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"

interface FileDropzoneProps {
  onDrop: (files: File[]) => void
  isUploading?: boolean
  uploadProgress?: number
  className?: string
  accept?: Record<string, string[]>
  multiple?: boolean
  maxSize?: number
  hint?: string
  children?: React.ReactNode
}

export function FileDropzone({
  onDrop,
  isUploading = false,
  uploadProgress = 0,
  className,
  accept,
  multiple = false,
  maxSize,
  hint,
  children,
}: FileDropzoneProps) {
  const [dragActive, setDragActive] = useState(false)

  const onDragEnter = useCallback(() => setDragActive(true), [])
  const onDragLeave = useCallback(() => setDragActive(false), [])

  const handleDrop = useCallback(
    (acceptedFiles: File[]) => {
      setDragActive(false)
      if (acceptedFiles.length > 0) {
        onDrop(acceptedFiles)
      }
    },
    [onDrop],
  )

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop: handleDrop,
    onDragEnter,
    onDragLeave,
    accept,
    multiple,
    maxSize,
  })

  return (
    <div
      {...getRootProps()}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-4 rounded-md border-2 border-dashed p-10 transition-colors",
        dragActive ? "border-primary bg-primary/5" : "border-muted-foreground/20",
        isUploading && "pointer-events-none opacity-70",
        className,
      )}
    >
      <input {...getInputProps()} />

      {children || (
        <>
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Upload className="h-6 w-6 text-primary" />
          </div>

          <div className="space-y-2 text-center">
            <p className="text-sm font-medium">
              {isDragActive ? "Drop files here" : "Drag and drop files here"}
            </p>
            <p className="text-xs text-muted-foreground">or click to browse files</p>
            {hint && (
              <p className="text-xs text-muted-foreground">{hint}</p>
            )}
          </div>

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation()
              open()
            }}
          >
            Select File
          </Button>
        </>
      )}

      {isUploading && (
        <div className="mt-4 w-full space-y-2">
          <Progress value={uploadProgress} className="h-1" />
          <p className="text-center text-xs text-muted-foreground">
            Uploading... {Math.round(uploadProgress)}%
          </p>
        </div>
      )}
    </div>
  )
}
