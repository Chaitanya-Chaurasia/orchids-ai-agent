# OrchidAI - AI Coding Assistant

OrchidAI is an intelligent coding assistant that helps you understand and work with your codebase more effectively. It uses vector embeddings to provide context-aware assistance.

## Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn

## Setup

1. First, install the required dependencies:
   ```bash
   npm install --legacy-peer-deps
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # On Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Getting Started

OrchidAI provides two main commands:

### 1. Initialize the Vector Store

Before using OrchidAI, you need to initialize the vector store which will index your codebase:

```bash
python orchid.py init
```

This command:
- Scans your codebase
- Creates vector embeddings of your code
- Stores them in a local Qdrant vector database
- Only needs to be run when you want to re-index your codebase

### 2. Run the AI Agent

To start interacting with OrchidAI:

```bash
python orchid.py run
```

This will start an interactive session where you can ask questions about your codebase and get AI-powered assistance.

## How It Works

1. **Vector Database**: OrchidAI uses Qdrant to store vector embeddings of your code, allowing for efficient semantic search and retrieval.

2. **Code Understanding**: The system analyzes your codebase to understand its structure, dependencies, and functionality.

3. **Context-Aware Assistance**: When you ask questions, OrchidAI uses the vector store to find relevant code snippets and provides accurate, context-aware responses.

## Development

To start the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser to see the application.

## Deployment

This is a Next.js application that can be deployed on Vercel or any other platform that supports Next.js applications.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
