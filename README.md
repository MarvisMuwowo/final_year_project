# Final Year Project - Security Analytics Platform

## Overview
This project is a FastAPI-based security analytics system that processes Windows security logs using an XGBoost machine learning model to detect and prioritize critical threats.

## Features
- Windows security log processing
- XGBoost-based threat classification
- SHAP explainability for AI decisions
- Role-based authentication system
- REST API for integration
- Event prioritization engine

## Tech Stack
- Python
- FastAPI
- XGBoost
- SHAP
- PostgreSQL / SQLite

## Project Structure
- backend/app/API → API endpoints
- backend/app/ML → ML model logic
- backend/app/service → preprocessing & event handling
- backend/database → database scripts

## How to Run
```bash
cd backend
pip install -r requirements.txt
uvicorn app.API.main:app --reload