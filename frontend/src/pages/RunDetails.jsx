import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { 
  ArrowLeft, 
  Download, 
  FileJson, 
  FileText, 
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Loader2
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const RunDetails = () => {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [run, setRun] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedRows, setExpandedRows] = useState({});

  useEffect(() => {
    const fetchRun = async () => {
      setIsLoading(true);
      try {
        const response = await axios.get(`${API}/runs/${runId}`);
        setRun(response.data);
      } catch (error) {
        toast.error("Failed to load run details");
        console.error(error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchRun();
  }, [runId]);

  const toggleExpanded = (idx) => {
    setExpandedRows(prev => ({
      ...prev,
      [idx]: !prev[idx]
    }));
  };

  const downloadJSON = async () => {
    try {
      const response = await axios.get(`${API}/report/${runId}`);
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `dq-report-${runId.slice(0, 8)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("JSON report downloaded");
    } catch (error) {
      toast.error("Failed to download JSON report");
    }
  };

  const downloadHTML = () => {
    window.open(`${API}/report/${runId}/html`, '_blank');
    toast.success("HTML report opened in new tab");
  };

  const getScoreColor = (score) => {
    if (score >= 90) return "text-emerald-600";
    if (score >= 70) return "text-blue-600";
    if (score >= 50) return "text-amber-600";
    return "text-red-600";
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

  const getStatusIcon = (status) => {
    switch (status) {
      case "PASS":
        return <CheckCircle2 className="w-4 h-4 text-emerald-500" strokeWidth={1.5} />;
      case "FAIL":
        return <XCircle className="w-4 h-4 text-red-500" strokeWidth={1.5} />;
      case "SKIP":
        return <AlertCircle className="w-4 h-4 text-slate-400" strokeWidth={1.5} />;
      default:
        return null;
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (isLoading) {
    return (
      <div className="container-main flex items-center justify-center py-16" data-testid="loading-state">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  if (!run) {
    return (
      <div className="container-main" data-testid="not-found">
        <Card className="text-center py-16">
          <CardContent>
            <h3 className="text-xl font-semibold text-slate-700 mb-2">Run Not Found</h3>
            <p className="text-slate-500 mb-4">The requested run could not be found</p>
            <Button onClick={() => navigate("/history")}>
              Back to History
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container-main" data-testid="run-details-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <Button 
            variant="ghost" 
            onClick={() => navigate(-1)}
            data-testid="back-btn"
          >
            <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
            Back
          </Button>
          <div>
            <h2 className="text-3xl font-black tracking-tight text-slate-900">
              Run Details
            </h2>
            <p className="text-slate-500 flex items-center gap-2">
              <span className="font-mono text-sm">{runId.slice(0, 8)}</span>
              <span>•</span>
              <Clock className="w-4 h-4" strokeWidth={1.5} />
              {formatDate(run.created_at)}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <Button 
            variant="outline" 
            onClick={downloadJSON}
            data-testid="download-json-btn"
          >
            <FileJson className="w-4 h-4 mr-2" strokeWidth={1.5} />
            Download JSON
          </Button>
          <Button 
            onClick={downloadHTML}
            data-testid="download-html-btn"
          >
            <FileText className="w-4 h-4 mr-2" strokeWidth={1.5} />
            View HTML Report
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {run.summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8" data-testid="summary-cards">
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-slate-500 mb-1">Overall Score</p>
              <p className={`text-4xl font-black ${getScoreColor(run.summary.score)}`}>
                {run.summary.score}%
              </p>
              <Progress value={run.summary.score} className="mt-2 h-2" />
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-slate-500 mb-1">Passed</p>
              <p className="text-3xl font-black text-emerald-600">{run.summary.passed}</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-slate-500 mb-1">Failed</p>
              <p className="text-3xl font-black text-red-600">{run.summary.failed}</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-slate-500 mb-1">Skipped</p>
              <p className="text-3xl font-black text-slate-400">{run.summary.skipped}</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-slate-500 mb-1">Total Rules</p>
              <p className="text-3xl font-black text-slate-900">{run.summary.total_rules}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Results Table */}
      <Card data-testid="results-card">
        <CardHeader>
          <CardTitle>Rule Results</CardTitle>
          <CardDescription>
            Detailed breakdown of all DQ checks
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2" data-testid="results-list">
            {run.results && run.results.map((result, idx) => (
              <Collapsible
                key={idx}
                open={expandedRows[idx]}
                onOpenChange={() => toggleExpanded(idx)}
              >
                <div 
                  className={`border rounded-lg transition-colors ${
                    result.status === 'FAIL' ? 'border-red-200 bg-red-50/30' : 
                    result.status === 'PASS' ? 'border-emerald-200 bg-emerald-50/30' : 
                    'border-slate-200'
                  }`}
                  data-testid={`result-item-${idx}`}
                >
                  <CollapsibleTrigger asChild>
                    <div className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-50/50 rounded-lg">
                      <div className="flex items-center gap-3">
                        {getStatusIcon(result.status)}
                        <div>
                          <p className="font-mono text-sm font-medium">{result.rule_name}</p>
                          <p className="text-sm text-slate-500">{result.description}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="text-sm font-mono">
                            <span className="text-slate-500">Metric:</span> {result.metric}
                          </p>
                          <p className="text-xs text-slate-400 font-mono">
                            Threshold: {result.threshold}
                          </p>
                        </div>
                        {getStatusBadge(result.status)}
                        {result.sample_rows && result.sample_rows.length > 0 ? (
                          expandedRows[idx] ? (
                            <ChevronUp className="w-4 h-4 text-slate-400" strokeWidth={1.5} />
                          ) : (
                            <ChevronDown className="w-4 h-4 text-slate-400" strokeWidth={1.5} />
                          )
                        ) : (
                          <div className="w-4" />
                        )}
                      </div>
                    </div>
                  </CollapsibleTrigger>
                  
                  {result.sample_rows && result.sample_rows.length > 0 && (
                    <CollapsibleContent>
                      <div className="px-4 pb-4">
                        <p className="text-sm font-semibold text-slate-700 mb-2">
                          Sample Bad Rows ({result.sample_rows.length})
                        </p>
                        <div className="sample-rows">
                          <pre className="whitespace-pre-wrap">
                            {JSON.stringify(result.sample_rows, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </CollapsibleContent>
                  )}
                </div>
              </Collapsible>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default RunDetails;
