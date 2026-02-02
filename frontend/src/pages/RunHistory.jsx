import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { 
  History, 
  RefreshCw, 
  ChevronRight, 
  FileSpreadsheet,
  Clock,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Loader2
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const RunHistory = () => {
  const navigate = useNavigate();
  const [runs, setRuns] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchRuns = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get(`${API}/runs`);
      setRuns(response.data.runs || []);
    } catch (error) {
      toast.error("Failed to load run history");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, []);

  const getScoreColor = (score) => {
    if (score >= 90) return "text-emerald-600";
    if (score >= 70) return "text-blue-600";
    if (score >= 50) return "text-amber-600";
    return "text-red-600";
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="w-5 h-5 text-emerald-500" strokeWidth={1.5} />;
      case "failed":
        return <XCircle className="w-5 h-5 text-red-500" strokeWidth={1.5} />;
      default:
        return <AlertCircle className="w-5 h-5 text-amber-500" strokeWidth={1.5} />;
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

  return (
    <div className="container-main" data-testid="run-history-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-3xl font-black tracking-tight text-slate-900 mb-2">
            Run History
          </h2>
          <p className="text-slate-600">
            View all previous data quality check runs
          </p>
        </div>
        <Button 
          variant="outline" 
          onClick={fetchRuns}
          disabled={isLoading}
          data-testid="refresh-btn"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} strokeWidth={1.5} />
          Refresh
        </Button>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-16" data-testid="loading-state">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
        </div>
      )}

      {/* Empty State */}
      {!isLoading && runs.length === 0 && (
        <Card className="text-center py-16" data-testid="empty-state">
          <CardContent>
            <div className="empty-state">
              <History className="empty-state-icon" strokeWidth={1.5} />
              <h3 className="text-xl font-semibold text-slate-700 mb-2">No Runs Yet</h3>
              <p className="text-slate-500 mb-4">
                Upload a CSV file and run DQ checks to see history here
              </p>
              <Button onClick={() => navigate("/")} data-testid="go-dashboard-btn">
                Go to Dashboard
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Runs List */}
      {!isLoading && runs.length > 0 && (
        <div className="space-y-4" data-testid="runs-list">
          {runs.map((run, idx) => (
            <Card 
              key={run.run_id} 
              className="card-hover cursor-pointer"
              onClick={() => navigate(`/runs/${run.run_id}`)}
              data-testid={`run-card-${idx}`}
            >
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    {getStatusIcon(run.status)}
                    
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <FileSpreadsheet className="w-4 h-4 text-slate-400" strokeWidth={1.5} />
                        <span className="font-semibold text-slate-900">
                          {run.filename || 'Unknown file'}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-slate-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5" strokeWidth={1.5} />
                          {formatDate(run.created_at)}
                        </span>
                        <span className="font-mono text-xs bg-slate-100 px-2 py-0.5 rounded">
                          {run.run_id.slice(0, 8)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    {run.summary && run.status === "completed" && (
                      <>
                        <div className="text-center">
                          <p className={`text-2xl font-black ${getScoreColor(run.summary.score)}`}>
                            {run.summary.score}%
                          </p>
                          <p className="text-xs text-slate-500">Score</p>
                        </div>
                        
                        <div className="w-32">
                          <div className="flex justify-between text-xs text-slate-500 mb-1">
                            <span className="text-emerald-600">{run.summary.passed} passed</span>
                            <span className="text-red-600">{run.summary.failed} failed</span>
                          </div>
                          <Progress 
                            value={(run.summary.passed / run.summary.total_rules) * 100} 
                            className="h-2"
                          />
                        </div>
                      </>
                    )}
                    
                    {run.status === "failed" && (
                      <span className="badge-fail">Failed</span>
                    )}
                    
                    <ChevronRight className="w-5 h-5 text-slate-400" strokeWidth={1.5} />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default RunHistory;
