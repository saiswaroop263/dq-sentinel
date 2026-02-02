from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from scipy import stats
import re
import io
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="DQ Sentinel API")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============= Pydantic Models =============

class DatasetResponse(BaseModel):
    dataset_id: str
    filename: str
    columns: List[str]
    row_count: int
    created_at: str

class RunConfig(BaseModel):
    dataset_id: str
    rules_config: Optional[Dict[str, Any]] = None

class DQResult(BaseModel):
    rule_name: str
    status: str
    metric: float
    threshold: float
    sample_rows: List[Dict[str, Any]]
    description: str

class RunResponse(BaseModel):
    run_id: str
    dataset_id: str
    status: str
    created_at: str
    completed_at: Optional[str]
    summary: Dict[str, Any]
    results: Optional[List[DQResult]] = None

class RunListItem(BaseModel):
    run_id: str
    dataset_id: str
    filename: str
    status: str
    created_at: str
    summary: Dict[str, Any]

# ============= DQ Rules Engine =============

class DQRulesEngine:
    """Data Quality Rules Engine with 10 configurable rules"""
    
    def __init__(self, df: pd.DataFrame, config: Optional[Dict] = None):
        self.df = df
        self.config = config or {}
        self.results = []
    
    def run_all_rules(self, previous_row_count: Optional[int] = None) -> List[Dict]:
        """Run all DQ rules and return results"""
        self.results = []
        
        # Rule 1: Required fields null rate
        self.check_null_rate()
        
        # Rule 2: Duplicate row detection
        self.check_duplicates()
        
        # Rule 3: Unique key check (id column)
        self.check_unique_key()
        
        # Rule 4: Numeric range validation
        self.check_numeric_range()
        
        # Rule 5: Regex validation (email)
        self.check_email_regex()
        
        # Rule 6: Regex validation (phone or zip)
        self.check_phone_zip_regex()
        
        # Rule 7: Date parse validation
        self.check_date_validation()
        
        # Rule 8: Allowed categorical values
        self.check_categorical_values()
        
        # Rule 9: Row count anomaly vs previous run
        self.check_row_count_anomaly(previous_row_count)
        
        # Rule 10: Outlier detection (IQR)
        self.check_outliers()
        
        return self.results
    
    def _add_result(self, rule_name: str, status: str, metric: float, threshold: float, 
                   sample_rows: List[Dict], description: str):
        # Clean sample rows - replace NaN/inf with None
        cleaned_rows = []
        for row in sample_rows[:5]:
            cleaned_row = {}
            for k, v in row.items():
                if pd.isna(v) or (isinstance(v, float) and (np.isinf(v) or np.isnan(v))):
                    cleaned_row[k] = None
                else:
                    cleaned_row[k] = v
            cleaned_rows.append(cleaned_row)
        
        # Clean metric value
        clean_metric = 0.0 if (pd.isna(metric) or np.isinf(metric)) else round(metric, 4)
        
        self.results.append({
            "rule_name": rule_name,
            "status": status,
            "metric": clean_metric,
            "threshold": threshold,
            "sample_rows": cleaned_rows,
            "description": description
        })
    
    def check_null_rate(self):
        """Rule 1: Check null rate in required fields"""
        threshold = self.config.get("null_rate_threshold", 0.05)
        required_cols = self.config.get("required_columns", list(self.df.columns)[:3])
        
        for col in required_cols:
            if col not in self.df.columns:
                continue
            null_rate = self.df[col].isna().sum() / len(self.df)
            status = "PASS" if null_rate <= threshold else "FAIL"
            
            null_rows = self.df[self.df[col].isna()].head(5).to_dict('records')
            self._add_result(
                f"Null Rate: {col}",
                status, null_rate, threshold, null_rows,
                f"Checks that column '{col}' has <= {threshold*100}% null values"
            )
    
    def check_duplicates(self):
        """Rule 2: Detect duplicate rows"""
        threshold = self.config.get("duplicate_threshold", 0.0)
        duplicates = self.df.duplicated(keep=False)
        dup_rate = duplicates.sum() / len(self.df)
        status = "PASS" if dup_rate <= threshold else "FAIL"
        
        dup_rows = self.df[duplicates].head(5).to_dict('records')
        self._add_result(
            "Duplicate Rows",
            status, dup_rate, threshold, dup_rows,
            "Detects fully duplicate rows in the dataset"
        )
    
    def check_unique_key(self):
        """Rule 3: Check unique key constraint (id column)"""
        id_cols = ['id', 'ID', 'order_id', 'customer_id', 'product_id']
        id_col = next((c for c in id_cols if c in self.df.columns), None)
        
        if id_col is None:
            self._add_result(
                "Unique Key Check",
                "SKIP", 0, 1.0, [],
                "No ID column found to check uniqueness"
            )
            return
        
        total = len(self.df)
        unique = self.df[id_col].nunique()
        uniqueness_rate = unique / total if total > 0 else 1.0
        status = "PASS" if uniqueness_rate >= 1.0 else "FAIL"
        
        duplicated_ids = self.df[self.df[id_col].duplicated(keep=False)]
        dup_rows = duplicated_ids.head(5).to_dict('records')
        
        self._add_result(
            f"Unique Key: {id_col}",
            status, uniqueness_rate, 1.0, dup_rows,
            f"Checks that '{id_col}' contains unique values"
        )
    
    def check_numeric_range(self):
        """Rule 4: Numeric range validation"""
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols[:3]:  # Check first 3 numeric columns
            min_val = self.config.get(f"{col}_min", self.df[col].min())
            max_val = self.config.get(f"{col}_max", self.df[col].max())
            
            # Use reasonable defaults for common columns
            if 'price' in col.lower() or 'amount' in col.lower():
                min_val = 0
                max_val = self.config.get(f"{col}_max", 100000)
            elif 'quantity' in col.lower() or 'qty' in col.lower():
                min_val = 0
                max_val = self.config.get(f"{col}_max", 10000)
            elif 'age' in col.lower():
                min_val = 0
                max_val = 120
            
            out_of_range = self.df[(self.df[col] < min_val) | (self.df[col] > max_val)]
            violation_rate = len(out_of_range) / len(self.df)
            status = "PASS" if violation_rate == 0 else "FAIL"
            
            self._add_result(
                f"Numeric Range: {col}",
                status, violation_rate, 0.0, out_of_range.head(5).to_dict('records'),
                f"Checks that '{col}' values are within [{min_val}, {max_val}]"
            )
    
    def check_email_regex(self):
        """Rule 5: Email regex validation"""
        email_cols = [c for c in self.df.columns if 'email' in c.lower()]
        
        if not email_cols:
            self._add_result(
                "Email Validation",
                "SKIP", 0, 1.0, [],
                "No email column found"
            )
            return
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        for col in email_cols:
            valid = self.df[col].astype(str).str.match(email_pattern, na=False)
            invalid_rate = (~valid).sum() / len(self.df)
            status = "PASS" if invalid_rate == 0 else "FAIL"
            
            invalid_rows = self.df[~valid].head(5).to_dict('records')
            self._add_result(
                f"Email Regex: {col}",
                status, invalid_rate, 0.0, invalid_rows,
                f"Validates email format in '{col}'"
            )
    
    def check_phone_zip_regex(self):
        """Rule 6: Phone or ZIP code regex validation"""
        phone_cols = [c for c in self.df.columns if 'phone' in c.lower()]
        zip_cols = [c for c in self.df.columns if 'zip' in c.lower() or 'postal' in c.lower()]
        
        if phone_cols:
            phone_pattern = r'^[\d\s\-\(\)\+]{7,20}$'
            for col in phone_cols:
                valid = self.df[col].astype(str).str.match(phone_pattern, na=False)
                invalid_rate = (~valid).sum() / len(self.df)
                status = "PASS" if invalid_rate == 0 else "FAIL"
                
                self._add_result(
                    f"Phone Regex: {col}",
                    status, invalid_rate, 0.0, 
                    self.df[~valid].head(5).to_dict('records'),
                    f"Validates phone number format in '{col}'"
                )
        
        if zip_cols:
            zip_pattern = r'^\d{5}(-\d{4})?$'  # US ZIP
            for col in zip_cols:
                valid = self.df[col].astype(str).str.match(zip_pattern, na=False)
                invalid_rate = (~valid).sum() / len(self.df)
                status = "PASS" if invalid_rate == 0 else "FAIL"
                
                self._add_result(
                    f"ZIP Regex: {col}",
                    status, invalid_rate, 0.0,
                    self.df[~valid].head(5).to_dict('records'),
                    f"Validates ZIP code format in '{col}'"
                )
        
        if not phone_cols and not zip_cols:
            self._add_result(
                "Phone/ZIP Validation",
                "SKIP", 0, 1.0, [],
                "No phone or ZIP column found"
            )
    
    def check_date_validation(self):
        """Rule 7: Date parse validation (no invalid/future dates)"""
        date_cols = [c for c in self.df.columns if 'date' in c.lower() or 'time' in c.lower()]
        
        if not date_cols:
            self._add_result(
                "Date Validation",
                "SKIP", 0, 1.0, [],
                "No date column found"
            )
            return
        
        today = datetime.now(timezone.utc).date()
        
        for col in date_cols:
            invalid_rows = []
            invalid_count = 0
            
            for idx, val in self.df[col].items():
                try:
                    if pd.isna(val):
                        invalid_count += 1
                        continue
                    parsed = pd.to_datetime(val)
                    if parsed.date() > today:
                        invalid_count += 1
                        invalid_rows.append(self.df.loc[idx].to_dict())
                except Exception:
                    invalid_count += 1
                    invalid_rows.append(self.df.loc[idx].to_dict())
            
            invalid_rate = invalid_count / len(self.df)
            status = "PASS" if invalid_rate == 0 else "FAIL"
            
            self._add_result(
                f"Date Validation: {col}",
                status, invalid_rate, 0.0, invalid_rows[:5],
                f"Validates date format and no future dates in '{col}'"
            )
    
    def check_categorical_values(self):
        """Rule 8: Allowed categorical values validation"""
        categorical_cols = self.df.select_dtypes(include=['object']).columns
        
        # Common categorical columns with expected values
        expected_values = {
            'status': ['pending', 'completed', 'shipped', 'cancelled', 'processing', 'delivered'],
            'category': None,  # Will be inferred
            'type': None,
            'payment_method': ['credit_card', 'debit_card', 'paypal', 'cash', 'bank_transfer'],
            'payment_status': ['paid', 'pending', 'failed', 'refunded']
        }
        
        found_categorical = False
        for col in categorical_cols:
            col_lower = col.lower()
            for key, allowed in expected_values.items():
                if key in col_lower:
                    found_categorical = True
                    if allowed is None:
                        # Infer allowed values from most common
                        allowed = self.df[col].value_counts().head(10).index.tolist()
                    
                    allowed_lower = [str(v).lower() for v in allowed]
                    valid = self.df[col].astype(str).str.lower().isin(allowed_lower)
                    invalid_rate = (~valid).sum() / len(self.df)
                    status = "PASS" if invalid_rate == 0 else "FAIL"
                    
                    self._add_result(
                        f"Categorical: {col}",
                        status, invalid_rate, 0.0,
                        self.df[~valid].head(5).to_dict('records'),
                        f"Validates allowed values in '{col}'"
                    )
                    break
        
        if not found_categorical:
            self._add_result(
                "Categorical Validation",
                "SKIP", 0, 1.0, [],
                "No recognized categorical column found"
            )
    
    def check_row_count_anomaly(self, previous_count: Optional[int]):
        """Rule 9: Row count anomaly vs previous run"""
        threshold = self.config.get("row_count_threshold", 0.3)
        current_count = len(self.df)
        
        if previous_count is None:
            self._add_result(
                "Row Count Anomaly",
                "SKIP", 0, threshold, [],
                "No previous run to compare row count"
            )
            return
        
        if previous_count == 0:
            change_rate = 1.0 if current_count > 0 else 0.0
        else:
            change_rate = abs(current_count - previous_count) / previous_count
        
        status = "PASS" if change_rate <= threshold else "FAIL"
        
        self._add_result(
            "Row Count Anomaly",
            status, change_rate, threshold, [],
            f"Current: {current_count}, Previous: {previous_count}, Change: {change_rate*100:.1f}%"
        )
    
    def check_outliers(self):
        """Rule 10: Outlier detection using IQR"""
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_cols) == 0:
            self._add_result(
                "Outlier Detection",
                "SKIP", 0, 0.05, [],
                "No numeric columns for outlier detection"
            )
            return
        
        threshold = self.config.get("outlier_threshold", 0.05)
        
        for col in numeric_cols[:2]:  # Check first 2 numeric columns
            Q1 = self.df[col].quantile(0.25)
            Q3 = self.df[col].quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = self.df[(self.df[col] < lower_bound) | (self.df[col] > upper_bound)]
            outlier_rate = len(outliers) / len(self.df)
            status = "PASS" if outlier_rate <= threshold else "FAIL"
            
            self._add_result(
                f"Outliers: {col}",
                status, outlier_rate, threshold,
                outliers.head(5).to_dict('records'),
                f"Detects outliers in '{col}' using IQR method"
            )


# ============= Demo Data Generator =============

def generate_ecommerce_demo_data(num_rows: int = 100) -> pd.DataFrame:
    """Generate e-commerce dataset with intentional data quality issues"""
    np.random.seed(42)
    
    # Generate base data
    order_ids = list(range(1, num_rows + 1))
    # Add duplicate IDs (intentional issue)
    order_ids[10] = order_ids[5]
    order_ids[20] = order_ids[15]
    
    customers = [f"customer_{i}" for i in np.random.randint(1, 50, num_rows)]
    
    products = ['Laptop', 'Phone', 'Tablet', 'Headphones', 'Monitor', 'Keyboard', 'Mouse', 'Camera']
    product_names = np.random.choice(products, num_rows)
    
    # Prices with some outliers (intentional issue)
    prices = np.random.uniform(10, 500, num_rows)
    prices[5] = -50  # Negative price (issue)
    prices[15] = 99999  # Extreme outlier (issue)
    
    quantities = np.random.randint(1, 10, num_rows)
    quantities[25] = -1  # Negative quantity (issue)
    
    # Emails with some invalid ones (intentional issue)
    emails = [f"user{i}@example.com" for i in range(num_rows)]
    emails[8] = "invalid-email"
    emails[18] = "missing@domain"
    emails[28] = "@nodomain.com"
    
    # Phone numbers with some invalid (intentional issue)
    phones = [f"555-{np.random.randint(100, 999)}-{np.random.randint(1000, 9999)}" for _ in range(num_rows)]
    phones[12] = "123"  # Too short
    phones[22] = "abc-def-ghij"  # Not a number
    
    # Dates with some invalid/future (intentional issue)
    base_date = datetime(2024, 1, 1)
    dates = [(base_date + pd.Timedelta(days=int(d))).strftime('%Y-%m-%d') 
             for d in np.random.randint(0, 365, num_rows)]
    dates[3] = "2030-12-31"  # Future date (issue)
    dates[13] = "invalid-date"  # Invalid date (issue)
    
    # Status with some invalid values (intentional issue)
    statuses = np.random.choice(['pending', 'completed', 'shipped', 'cancelled'], num_rows)
    statuses = list(statuses)
    statuses[7] = "UNKNOWN_STATUS"  # Invalid status (issue)
    statuses[17] = "InvalidValue"  # Invalid status (issue)
    
    # ZIP codes with some invalid (intentional issue)
    zips = [f"{np.random.randint(10000, 99999)}" for _ in range(num_rows)]
    zips[9] = "ABC"  # Invalid ZIP
    zips[19] = "1234"  # Too short
    
    # Add some null values (intentional issue)
    df = pd.DataFrame({
        'order_id': order_ids,
        'customer_id': customers,
        'product': product_names,
        'price': prices,
        'quantity': quantities,
        'email': emails,
        'phone': phones,
        'order_date': dates,
        'status': statuses,
        'zip_code': zips
    })
    
    # Add null values
    df.loc[4, 'customer_id'] = None
    df.loc[14, 'product'] = None
    df.loc[24, 'email'] = None
    
    # Add duplicate rows
    df = pd.concat([df, df.iloc[[30, 31]]], ignore_index=True)
    
    return df


# ============= API Endpoints =============

@api_router.get("/")
async def root():
    return {"message": "DQ Sentinel API", "version": "1.0.0"}


@api_router.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Upload CSV file and store dataset metadata"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        dataset_id = str(uuid.uuid4())
        
        # Store sample rows (up to 1000)
        sample_rows = df.head(1000).to_dict('records')
        
        # Clean sample rows for MongoDB (convert NaN to None)
        for row in sample_rows:
            for key, value in row.items():
                if pd.isna(value):
                    row[key] = None
        
        dataset_doc = {
            "dataset_id": dataset_id,
            "filename": file.filename,
            "columns": list(df.columns),
            "row_count": len(df),
            "sample_rows": sample_rows,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.datasets.insert_one(dataset_doc)
        
        return {
            "dataset_id": dataset_id,
            "filename": file.filename,
            "columns": list(df.columns),
            "row_count": len(df),
            "created_at": dataset_doc["created_at"]
        }
    
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/run")
async def run_dq_checks(config: RunConfig):
    """Run DQ checks on a dataset"""
    # Get dataset
    dataset = await db.datasets.find_one(
        {"dataset_id": config.dataset_id},
        {"_id": 0}
    )
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    run_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)
    
    try:
        # Reconstruct DataFrame from sample rows
        df = pd.DataFrame(dataset["sample_rows"])
        
        # Get previous run row count for anomaly detection
        previous_run = await db.runs.find_one(
            {"dataset_id": config.dataset_id, "status": "completed"},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        previous_row_count = previous_run.get("row_count") if previous_run else None
        
        # Run DQ engine
        engine = DQRulesEngine(df, config.rules_config)
        results = engine.run_all_rules(previous_row_count)
        
        # Calculate summary
        total_rules = len(results)
        passed = sum(1 for r in results if r["status"] == "PASS")
        failed = sum(1 for r in results if r["status"] == "FAIL")
        skipped = sum(1 for r in results if r["status"] == "SKIP")
        score = (passed / (total_rules - skipped)) * 100 if (total_rules - skipped) > 0 else 0
        
        end_time = datetime.now(timezone.utc)
        
        # Store run
        run_doc = {
            "run_id": run_id,
            "dataset_id": config.dataset_id,
            "filename": dataset["filename"],
            "status": "completed",
            "created_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "row_count": len(df),
            "summary": {
                "total_rules": total_rules,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "score": round(score, 1)
            },
            "timings": {
                "duration_ms": int((end_time - start_time).total_seconds() * 1000)
            }
        }
        await db.runs.insert_one(run_doc)
        
        # Store DQ results
        for result in results:
            result_doc = {
                "run_id": run_id,
                **result
            }
            await db.dq_results.insert_one(result_doc)
        
        return {
            "run_id": run_id,
            "dataset_id": config.dataset_id,
            "status": "completed",
            "created_at": run_doc["created_at"],
            "completed_at": run_doc["completed_at"],
            "summary": run_doc["summary"],
            "results": results
        }
    
    except Exception as e:
        logger.error(f"Error running DQ checks: {e}")
        # Store failed run
        await db.runs.insert_one({
            "run_id": run_id,
            "dataset_id": config.dataset_id,
            "filename": dataset["filename"],
            "status": "failed",
            "created_at": start_time.isoformat(),
            "error": str(e),
            "summary": {"error": str(e)}
        })
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/demo")
async def run_demo():
    """Generate demo e-commerce dataset and run DQ checks"""
    try:
        # Generate demo data
        df = generate_ecommerce_demo_data(100)
        dataset_id = str(uuid.uuid4())
        
        # Clean data for MongoDB
        sample_rows = df.to_dict('records')
        for row in sample_rows:
            for key, value in row.items():
                if pd.isna(value):
                    row[key] = None
        
        # Store dataset
        dataset_doc = {
            "dataset_id": dataset_id,
            "filename": "demo_ecommerce_data.csv",
            "columns": list(df.columns),
            "row_count": len(df),
            "sample_rows": sample_rows,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_demo": True
        }
        await db.datasets.insert_one(dataset_doc)
        
        # Run DQ checks
        config = RunConfig(dataset_id=dataset_id)
        result = await run_dq_checks(config)
        
        return result
    
    except Exception as e:
        logger.error(f"Error running demo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/runs")
async def get_runs():
    """Get all DQ runs"""
    runs = await db.runs.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"runs": runs}


@api_router.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get a specific run with its results"""
    run = await db.runs.find_one({"run_id": run_id}, {"_id": 0})
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Get results
    results = await db.dq_results.find({"run_id": run_id}, {"_id": 0}).to_list(100)
    
    return {
        **run,
        "results": results
    }


@api_router.get("/report/{run_id}")
async def get_report_json(run_id: str):
    """Get DQ report as JSON"""
    run = await db.runs.find_one({"run_id": run_id}, {"_id": 0})
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    results = await db.dq_results.find({"run_id": run_id}, {"_id": 0}).to_list(100)
    
    # Get dataset info
    dataset = await db.datasets.find_one(
        {"dataset_id": run["dataset_id"]},
        {"_id": 0, "sample_rows": 0}
    )
    
    report = {
        "report_type": "DQ Sentinel Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run": run,
        "dataset": dataset,
        "results": results
    }
    
    return JSONResponse(content=report)


@api_router.get("/report/{run_id}/html", response_class=HTMLResponse)
async def get_report_html(run_id: str):
    """Get DQ report as HTML"""
    run = await db.runs.find_one({"run_id": run_id}, {"_id": 0})
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    results = await db.dq_results.find({"run_id": run_id}, {"_id": 0}).to_list(100)
    
    # Generate HTML report
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DQ Sentinel Report - {run_id[:8]}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Inter', -apple-system, sans-serif; background: #F8FAFC; color: #0F172A; padding: 40px; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            h1 {{ font-family: 'Chivo', sans-serif; font-weight: 900; font-size: 2.5rem; margin-bottom: 8px; }}
            h2 {{ font-family: 'Chivo', sans-serif; font-weight: 700; font-size: 1.5rem; margin: 24px 0 16px; }}
            .subtitle {{ color: #64748B; margin-bottom: 32px; }}
            .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }}
            .card {{ background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 20px; }}
            .card-label {{ font-size: 0.875rem; color: #64748B; margin-bottom: 4px; }}
            .card-value {{ font-size: 2rem; font-weight: 700; }}
            .score {{ color: #2563EB; }}
            .passed {{ color: #10B981; }}
            .failed {{ color: #EF4444; }}
            table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #E2E8F0; border-radius: 8px; overflow: hidden; }}
            th {{ background: #F8FAFC; text-align: left; padding: 12px 16px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #E2E8F0; }}
            td {{ padding: 12px 16px; border-bottom: 1px solid #E2E8F0; font-size: 0.875rem; }}
            tr:last-child td {{ border-bottom: none; }}
            .badge {{ display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 500; }}
            .badge-pass {{ background: #D1FAE5; color: #065F46; }}
            .badge-fail {{ background: #FEE2E2; color: #991B1B; }}
            .badge-skip {{ background: #F1F5F9; color: #64748B; }}
            .mono {{ font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; }}
            .footer {{ margin-top: 40px; text-align: center; color: #64748B; font-size: 0.875rem; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>DQ Sentinel Report</h1>
            <p class="subtitle">Run ID: <span class="mono">{run_id}</span> | Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
            
            <div class="summary">
                <div class="card">
                    <div class="card-label">Overall Score</div>
                    <div class="card-value score">{run.get('summary', {}).get('score', 0)}%</div>
                </div>
                <div class="card">
                    <div class="card-label">Passed</div>
                    <div class="card-value passed">{run.get('summary', {}).get('passed', 0)}</div>
                </div>
                <div class="card">
                    <div class="card-label">Failed</div>
                    <div class="card-value failed">{run.get('summary', {}).get('failed', 0)}</div>
                </div>
                <div class="card">
                    <div class="card-label">Total Rules</div>
                    <div class="card-value">{run.get('summary', {}).get('total_rules', 0)}</div>
                </div>
            </div>
            
            <h2>Rule Results</h2>
            <table>
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
    """
    
    for result in results:
        status_class = f"badge-{result['status'].lower()}"
        html += f"""
                    <tr>
                        <td class="mono">{result['rule_name']}</td>
                        <td><span class="badge {status_class}">{result['status']}</span></td>
                        <td class="mono">{result['metric']}</td>
                        <td class="mono">{result['threshold']}</td>
                        <td>{result['description']}</td>
                    </tr>
        """
    
    html += f"""
                </tbody>
            </table>
            
            <div class="footer">
                <p>Generated by DQ Sentinel | {datetime.now(timezone.utc).strftime('%Y')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html)


@api_router.get("/datasets")
async def get_datasets():
    """Get all datasets"""
    datasets = await db.datasets.find(
        {},
        {"_id": 0, "sample_rows": 0}
    ).sort("created_at", -1).to_list(100)
    return {"datasets": datasets}


# Include router and middleware
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create indexes on startup
@app.on_event("startup")
async def startup_db():
    # Create indexes
    await db.runs.create_index("created_at")
    await db.runs.create_index("run_id")
    await db.dq_results.create_index("run_id")
    await db.datasets.create_index("dataset_id")
    logger.info("Database indexes created")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
