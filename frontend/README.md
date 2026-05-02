# AI Compiler - Frontend UI

## Overview
Interactive Streamlit web interface for the AI Compiler system.

## Features

### 3-Column Layout
1. **Input Code** - C/C++ source code editor with demo program selector
2. **Pipeline Status** - Real-time compilation, optimization, and verification status
3. **Results** - Metrics, IR statistics, and download options

### Demo Programs
- **Matrix Multiply** - Performance optimization demo (loop invariant code motion)
- **Unsafe String Handling** - Memory safety demo (bounds checking injection)
- **Fibonacci** - Redundant computation elimination
- **Simple Add** - Basic compilation test

### Pipeline Steps
1. **Compile to IR** - Uses `clang` to generate LLVM IR
2. **AI Optimization** - Applies transformations (currently mock, awaiting Bob integration)
3. **Formal Verification** - Uses Alive2 + Z3 to prove correctness

## Running the UI

### Option 1: Using pipx (Recommended)
```bash
brew install pipx
pipx install streamlit
streamlit run frontend/app.py
```

### Option 2: Using pip in virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install streamlit
streamlit run frontend/app.py
```

### Option 3: Direct installation
```bash
pip3 install --user streamlit
streamlit run frontend/app.py
```

The UI will be available at: `http://localhost:8501`

## Testing

Test the UI components without running Streamlit:
```bash
python3 frontend/test_ui.py
```

## UI Components

### Sidebar
- Demo program selector
- Program descriptions
- Settings (Show IR, Show Diff)
- About section

### Main Area
- **Column 1**: Source code editor with compile button
- **Column 2**: Pipeline status with step-by-step progress
- **Column 3**: Results with metrics and download options

### Status Indicators
- 🔄 In Progress (blue)
- ✅ Success (green)
- ❌ Error (red)

## Integration Status

### ✅ Completed
- 3-column Streamlit layout
- Demo program selector with 4 programs
- MCP server integration (compile_to_ir, optimize_ir_pass, validate_translation)
- Real-time status updates
- IR diff visualization
- Alive2 output rendering
- Metrics display
- Download functionality

### 🔄 Pending
- Bob agent integration (@ir-architect, @memory-sentinel)
- Supervisor orchestration
- Real AI-driven optimizations
- Performance benchmarking
- Memory safety check visualization

## File Structure
```
frontend/
├── app.py           # Main Streamlit application
├── test_ui.py       # UI component tests
└── README.md        # This file
```

## Dependencies
- streamlit >= 1.35.0
- server.mcp_server (compile_to_ir, optimize_ir_pass, validate_translation)

## Next Steps
1. Integrate Bob Custom Modes
2. Add supervisor orchestration
3. Implement real-time optimization metrics
4. Add performance benchmarking
5. Create demo video recording feature