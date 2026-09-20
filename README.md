# 🛡️ MedVerify — Autonomous Medicine Safety & Regulatory Verification Intelligence

[![Deploy Frontend](https://img.shields.io/badge/AWS%20Amplify-Deployed-success?style=for-the-badge&logo=awsamplify)](https://main.dy5d9rfcvv5lz.amplifyapp.com/)
[![Deploy Backend](https://img.shields.io/badge/AWS%20Lambda-API%20Gateway-orange?style=for-the-badge&logo=awslambda)](https://s61okz6xz9.execute-api.us-east-1.amazonaws.com/health)
[![UI Framework](https://img.shields.io/badge/UI-AWS%20Cloudscape-232F3E?style=for-the-badge&logo=amazonwebservices)](https://cloudscape.design/)
[![AI Models](https://img.shields.io/badge/AI-Groq%20%7C%20Gemini%202.5-blue?style=for-the-badge&logo=google)](https://deepmind.google/technologies/gemini/)

> **MedVerify** is an enterprise-grade AI intelligence system designed to combat counterfeit, spurious, and Not of Standard Quality (NSQ) pharmaceuticals in India. By combining official **CDSCO** (Central Drugs Standard Control Organisation) regulatory gazette data, **Multimodal Vision OCR**, **Multi-Tier Autonomous Agents**, and real-time **Community Crowd-Sourced Signals**, MedVerify provides instant verification and clinical investigations for consumers, healthcare workers, and pharmacists.

---

## 🌐 Live Deployments

| Component | Production URL | Description |
| :--- | :--- | :--- |
| **Frontend Application** | **[https://main.dy5d9rfcvv5lz.amplifyapp.com/](https://main.dy5d9rfcvv5lz.amplifyapp.com/)** | Hosted on **AWS Amplify** (SPA with Cloudscape Design System) |
| **Backend API Gateway** | **[https://s61okz6xz9.execute-api.us-east-1.amazonaws.com](https://s61okz6xz9.execute-api.us-east-1.amazonaws.com)** | Serverless **AWS Lambda** (Python 3.12 + FastAPI + Lambda Web Adapter) |
| **API Documentation** | **[https://s61okz6xz9.execute-api.us-east-1.amazonaws.com/docs](https://s61okz6xz9.execute-api.us-east-1.amazonaws.com/docs)** | Interactive Swagger UI for testing API endpoints |
| **Health Check** | **[https://s61okz6xz9.execute-api.us-east-1.amazonaws.com/health](https://s61okz6xz9.execute-api.us-east-1.amazonaws.com/health)** | Live system status & region health check |

---

## 🧩 Key Capabilities

- **📸 Multimodal Packaging OCR:** Upload or snap photos of blister packs, syrups, or vials. Google Gemini Vision extracts batch numbers, expiry dates, and manufacturer details with automated image preprocessing.
- **⚡ Quick Regulatory Verification:** Sub-second queries directly against CDSCO national alert tables in Amazon DynamoDB for flagged NSQ and spurious drug batches.
- **🧠 Multi-Tier AI Agent Orchestration:**
  - **Tier Orchestrator (Groq / LLaMA-3.3-70B):** Dynamically classifies query complexity, intent, and missing data.
  - **Skill Agent with .agents/skills:** Autonomous agent that loads modular SKILL.md specifications to execute targeted checks (batch verification, manufacturer risk profiling, fuzzy drug search).
  - **Deep Autonomous Investigator (deepagents + TodoListMiddleware):** Decomposes ambiguous or suspicious packaging claims into structured multi-step investigation plans with full audit traces.
- **👥 Crowd-Sourced Community Alerts:** Real-world signals where consumers and pharmacists can submit adverse event reports and suspected fake batches.
- **🔐 Enterprise Authentication:** Fully integrated with **Amazon Cognito User Pools** supporting consumer and verified pharmacist role-based access.
- **🎨 AWS Cloudscape Design System:** Intuitive healthcare workspace built with Amazon production Cloudscape component library.

---

## 🏗️ System Architecture

`mermaid
flowchart TD
    subgraph Client [Client Layer]
        UI[AWS Amplify SPA: React + TypeScript + Cloudscape]
    end

    subgraph Auth [Authentication]
        Cognito[Amazon Cognito User Pool: JWT Auth & RBAC]
    end

    subgraph API [Serverless Backend]
        APIGW[Amazon API Gateway HTTP API]
        Lambda[AWS Lambda Web Adapter: FastAPI / Python 3.12]
    end

    subgraph Agents [Autonomous Agent Layer]
        Orchestrator[Tier Orchestrator: Groq / LLaMA-3.3-70B]
        SkillAgent[Skill Agent: .agents/skills Specs]
        DeepAgent[Deep Agent: deepagents + TodoListMiddleware]
        GeminiOCR[Multimodal Vision: Gemini 2.5 Flash]
    end

    subgraph Storage [AWS Data Layer]
        DDB_Batches[(DynamoDB: MedVerify_Batches)]
        DDB_Reports[(DynamoDB: MedVerify_Reports)]
        DDB_Sessions[(DynamoDB: MedVerify_Sessions)]
        DDB_Mfr[(DynamoDB: MedVerify_Manufacturers)]
        S3_Uploads[S3: Packaging Photos]
        S3_Docs[S3: CDSCO Raw Gazette Docs]
    end

    UI --> APIGW
    UI -.-> Cognito
    APIGW --> Lambda
    Lambda --> Orchestrator
    
    Orchestrator --> SkillAgent
    Orchestrator --> GeminiOCR
    Orchestrator --> DeepAgent

    SkillAgent --> DDB_Batches
    SkillAgent --> DDB_Mfr
    SkillAgent --> DDB_Reports
    
    DeepAgent --> Storage
    GeminiOCR --> S3_Uploads
    Lambda --> DDB_Sessions
`

---

## 🤖 Agent Framework & Model Matrix

| Role | Framework | Underlying Model | Tool Selection Mechanism | Primary Responsibilities |
| :--- | :--- | :--- | :--- | :--- |
| **Tier Orchestrator** | **Strands SDK** | llama-3.3-70b-versatile (Groq) | LLM classification | Evaluates query intent; routes to Quick Check, Skill Agent, or Deep Agent. |
| **Multimodal OCR** | **Google GenAI SDK** | gemini-2.5-flash | Direct Vision API | Extracts batch numbers, drug names, and dates from blister pack images. |
| **Skill Agent** | **Strands SDK** | llama-3.3-70b-versatile (Groq) | Dynamic selection via SKILL.md | Executes CDSCO regulatory batch lookups, manufacturer track records, and crowd signals. |
| **Deep Investigator** | **deepagents** | gemini-2.5-flash | TodoListMiddleware + Multi-step tools | Formulates multi-step research hypotheses, queries registries, and summarizes clinical risks. |

### Modular SKILL.md Directory (.agents/skills/)
The Skill Agent dynamically ingests modular markdown specifications:
- check-batch — CDSCO regulatory records & spurious alerts lookup.
- get-community-reports — Adverse reactions & crowd-sourced counterfeit flags.
- get-manufacturer-history — Manufacturer risk profiling & past flagged batches.
- search-drug — Fuzzy matching for OCR typos and partial brand names.
- get-notice — Raw regulatory gazette notice citations from S3.
- get-case-history — Audit trails and past user verification sessions.

---

## 📡 Key API Endpoints

| Method | Route | Description |
| :--- | :--- | :--- |
| GET | /health | Service health status and AWS region info |
| POST | /check | Instant batch check against CDSCO regulatory database |
| POST | /investigate | Full multimodal investigation with photo extraction |
| POST | /investigate/deep | Autonomous deep agent investigation with task breakdown |
| POST | /reports | Submit community adverse event or fake medicine report |
| GET | /reports/batch/{batch_no} | Retrieve crowd safety reports for a batch |
| GET | /batches/{batch_no} | Batch regulatory record & manufacturer details |
| GET | /manufacturers/{id}/history | Manufacturer risk tier & past violations |
| POST | /uploads/presign | S3 pre-signed upload URL for packaging photos |
| POST | /auth/login | Cognito user sign-in & JWT token issuance |
| POST | /auth/signup | Register consumer or pharmacist account |

---

## 💻 Local Development

### Prerequisites
- Python 3.12+
- Node.js 20+ & npm
- AWS CLI configured with active credentials

### 1. Backend Setup

`ash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Fill in your GROQ_API_KEY, GEMINI_API_KEY, and AWS table names

# Start FastAPI dev server
uvicorn src.main:app --reload --port 8000
`

### 2. Frontend Setup

`ash
cd frontend

# Install packages
npm install

# Start Vite development server
npm run dev
# Open http://localhost:3000
`

---

## ⚠️ Regulatory Disclaimer

> MedVerify is an assistive intelligence verification system. Absence of a CDSCO recall flag does **not** guarantee a medicine's safety or authenticity. Patients and healthcare practitioners must consult qualified medical professionals and authorized drug control officers for formal pharmaceutical safety determinations.

---

## 📄 License
This project is licensed under the MIT License — see the LICENSE file for details.
