import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { 
  Upload, 
  Play, 
  FileSpreadsheet, 
  CheckCircle2, 
  XCircle, 
  AlertCircle,
  Loader2,
  Sparkles,
  ArrowRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Dashboard = () => {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [uploadedDataset, setUploadedDataset] = useState(null);
  const [runResult, setRunResult] = useState(null);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.name.endsWith('.csv')) {
      setFile(droppedFile);
      setUploadedDataset(null);
      setRunResult(null);
    } else {
      toast.error("Please upload a CSV file");
    }
  }, []);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setUploadedDataset(null);
      setRunResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setUploadedDataset(response.data);
      toast.success("Dataset uploaded successfully!");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to upload file");
    } finally {
      setIsUploading(false);
    }
  };

  const handleRunChecks = async () => {
    if (!uploadedDataset) return;
    
    setIsRunning(true);
    try {
      const response = await axios.post(`${API}/run`, {
        dataset_id: uploadedDataset.dataset_id
      });
      setRunResult(response.data);
      toast.success("DQ checks completed!");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to run checks");
    } finally {
      setIsRunning(false);
    }
  };

  const handleDemo = async () => {
    setIsRunning(true);
    setFile(null);
    setUploadedDataset(null);
    setRunResult(null);

    try {
      const response = await axios.post(`${API}/demo`);
      setRunResult(response.data);
      toast.success("Demo completed! Check the results below.");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to run demo");
    } finally {
      setIsRunning(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 90) return "score-excellent";
    if (score >= 70) return "score-good";
    if (score >= 50) return "score-warning";
    return "score-critical";
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "PASS":
        return <span className="badge-pass">PASS</span>;
      case "FAIL":
        return <span className="badge-fail">FAIL</span>;
      case "SKIP":
        return <span className="badge-skip">SKIP</span>;
      default:
        return <span className="badge-warning">{status}</span>;
    }
  };

  return (
    <div className="container-main" data-testid="dashboard-page">
      {/* Hero Section */}
      <div className="mb-8">
        <h2 className="text-3xl font-black tracking-tight text-slate-900 mb-2">
          Data Quality Dashboard
        </h2>
        <p className="text-slate-600">
          Upload your CSV file to run comprehensive data quality checks
        </p>
      </div>

      {/* Bento Grid */}
      <div className="bento-grid mb-8">
        {/* Upload Card */}
        <Card className="full-width card-hover" data-testid="upload-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="w-5 h-5 text-blue-600" strokeWidth={1.5} />
              Upload Dataset
            </CardTitle>
            <CardDescription>
              Drag and drop a CSV file or click to browse
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              className={`upload-zone ${isDragging ? 'dragging' : ''} ${file ? 'border-emerald-400 bg-emerald-50/50' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => document.getElementById('file-input').click()}
              data-testid="upload-zone"
            >
              <input
                id="file-input"
                type="file"
                accept=".csv"
                onChange={handleFileSelect}
                className="hidden"
                data-testid="file-input"
              />
              
              {file ? (
                <div className="flex flex-col items-center gap-3">
                  <FileSpreadsheet className="w-12 h-12 text-emerald-600" strokeWidth={1.5} />
                  <div>
                    <p className="font-semibold text-slate-900">{file.name}</p>
                    <p className="text-sm text-slate-500">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3">
                  <Upload className="w-12 h-12 text-slate-400 group-hover:text-blue-600 transition-colors" strokeWidth={1.5} />
                  <div>
                    <p className="font-semibold text-slate-700">Drop your CSV file here</p>
                    <p className="text-sm text-slate-500">or click to browse</p>
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center gap-4 mt-6">
              <Button
                onClick={handleUpload}
                disabled={!file || isUploading}
                className="flex-1"
                data-testid="upload-btn"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2" strokeWidth={1.5} />
                    Upload File
                  </>
                )}
              </Button>
              
              <Button
                onClick={handleRunChecks}
                disabled={!uploadedDataset || isRunning}
                variant="secondary"
                className="flex-1"
                data-testid="run-checks-btn"
              >
                {isRunning && uploadedDataset ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Running...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" strokeWidth={1.5} />
                    Run DQ Checks
                  </>
                )}
              </Button>
            </div>

            {uploadedDataset && (
              <div className="mt-4 p-4 bg-emerald-50 rounded-lg border border-emerald-200 animate-fade-in" data-testid="upload-success">
                <div className="flex items-center gap-2 text-emerald-700 mb-2">
                  <CheckCircle2 className="w-5 h-5" strokeWidth={1.5} />
                  <span className="font-semibold">Dataset Ready</span>
                </div>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-slate-500">Filename</p>
                    <p className="font-mono text-slate-900">{uploadedDataset.filename}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Columns</p>
                    <p className="font-mono text-slate-900">{uploadedDataset.columns.length}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Rows</p>
                    <p className="font-mono text-slate-900">{uploadedDataset.row_count}</p>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Demo Card */}
        <Card className="score-card-lg card-hover" data-testid="demo-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-500" strokeWidth={1.5} />
              Try Demo
            </CardTitle>
            <CardDescription>
              Generate sample e-commerce data with intentional issues
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-600 mb-4">
              Click below to generate a demo dataset with various data quality issues 
              (nulls, duplicates, invalid values) and run all 10 DQ checks.
            </p>
            <Button
              onClick={handleDemo}
              disabled={isRunning}
              variant="outline"
              className="w-full border-amber-300 hover:bg-amber-50 hover:border-amber-400"
              data-testid="demo-btn"
            >
              {isRunning && !uploadedDataset ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Generating Demo...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  Run Demo
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Quick Stats Card */}
        <Card className="score-card-lg card-hover" data-testid="stats-card">
          <CardHeader>
            <CardTitle>DQ Rules</CardTitle>
            <CardDescription>10 comprehensive checks</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="text-sm space-y-2 text-slate-600">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" strokeWidth={1.5} />
                Null rate validation
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" strokeWidth={1.5} />
                Duplicate detection
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" strokeWidth={1.5} />
                Regex validation (email, phone)
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" strokeWidth={1.5} />
                Outlier detection (IQR)
              </li>
              <li className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-blue-500" strokeWidth={1.5} />
                + 6 more rules
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Results Section */}
      {runResult && (
        <div className="animate-fade-in" data-testid="results-section">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-2xl font-bold text-slate-900">DQ Check Results</h3>
            <Button 
              variant="outline" 
              onClick={() => navigate(`/runs/${runResult.run_id}`)}
              data-testid="view-details-btn"
            >
              View Full Report
              <ArrowRight className="w-4 h-4 ml-2" strokeWidth={1.5} />
            </Button>
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <Card data-testid="score-card">
              <CardContent className="pt-6">
                <p className="text-sm text-slate-500 mb-1">Overall Score</p>
                <p className={`text-4xl font-black ${getScoreColor(runResult.summary.score)}`}>
                  {runResult.summary.score}%
                </p>
                <Progress 
                  value={runResult.summary.score} 
                  className="mt-2 h-2"
                />
              </CardContent>
            </Card>
            
            <Card data-testid="passed-card">
              <CardContent className="pt-6">
                <p className="text-sm text-slate-500 mb-1">Passed</p>
                <p className="text-4xl font-black text-emerald-600">
                  {runResult.summary.passed}
                </p>
                <p className="text-sm text-slate-500 mt-1">rules</p>
              </CardContent>
            </Card>
            
            <Card data-testid="failed-card">
              <CardContent className="pt-6">
                <p className="text-sm text-slate-500 mb-1">Failed</p>
                <p className="text-4xl font-black text-red-600">
                  {runResult.summary.failed}
                </p>
                <p className="text-sm text-slate-500 mt-1">rules</p>
              </CardContent>
            </Card>
            
            <Card data-testid="total-card">
              <CardContent className="pt-6">
                <p className="text-sm text-slate-500 mb-1">Total Rules</p>
                <p className="text-4xl font-black text-slate-900">
                  {runResult.summary.total_rules}
                </p>
                <p className="text-sm text-slate-500 mt-1">executed</p>
              </CardContent>
            </Card>
          </div>

          {/* Results Table */}
          <Card data-testid="results-table-card">
            <CardHeader>
              <CardTitle>Rule Results</CardTitle>
              <CardDescription>
                Run ID: <span className="font-mono">{runResult.run_id.slice(0, 8)}</span>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="dq-table" data-testid="results-table">
                  <thead>
                    <tr>
                      <th>Rule Name</th>
                      <th>Status</th>
                      <th>Metric</th>
                      <th>Threshold</th>
                      <th>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runResult.results.map((result, idx) => (
                      <tr key={idx} data-testid={`result-row-${idx}`}>
                        <td>
                          <span className="rule-name">{result.rule_name}</span>
                        </td>
                        <td>{getStatusBadge(result.status)}</td>
                        <td className="font-mono text-sm">{result.metric}</td>
                        <td className="font-mono text-sm">{result.threshold}</td>
                        <td className="text-slate-600 text-sm">{result.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
