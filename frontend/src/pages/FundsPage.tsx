import { useState, useCallback } from "react"
import { PageHeader } from "@/components/PageHeader"
import { FileDropzone } from "@/components/ui/file-dropzone"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { FileSpreadsheet } from "lucide-react"

export function FundsPage() {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleDrop = useCallback((files: File[]) => {
    setError(null)
    const file = files[0]
    if (file) {
      setUploadedFile(file)
    }
  }, [])

  return (
    <div>
      <PageHeader
        title="Funds"
        description="Upload and manage fund performance data."
      />

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {uploadedFile ? (
        <div className="rounded-lg border p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
              <FileSpreadsheet className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium">{uploadedFile.name}</p>
              <p className="text-xs text-muted-foreground">
                {(uploadedFile.size / 1024).toFixed(1)} KB
              </p>
            </div>
          </div>
          <p className="text-sm text-muted-foreground">
            To process this file, start a <strong>New Allocation</strong> from the sidebar.
          </p>
        </div>
      ) : (
        <FileDropzone
          onDrop={handleDrop}
          accept={{
            "text/csv": [".csv"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
            "application/vnd.ms-excel": [".xls"],
          }}
          hint="Supports CSV, XLS, and XLSX files"
        />
      )}
    </div>
  )
}
