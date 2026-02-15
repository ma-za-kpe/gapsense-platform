#!/bin/bash
# Viztracer Helper Script for GapSense
#
# Trace execution flow and visualize performance bottlenecks

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

VIZTRACER="/Users/mac/Library/Caches/pypoetry/virtualenvs/gapsense-1Ckj6UrV-py3.13/bin/viztracer"
VIZVIEWER="/Users/mac/Library/Caches/pypoetry/virtualenvs/gapsense-1Ckj6UrV-py3.13/bin/vizviewer"
TRACES_DIR="./traces"

# Create traces directory
mkdir -p "$TRACES_DIR"

# Show usage
if [ $# -eq 0 ]; then
    echo -e "${BLUE}Viztracer Helper for GapSense${NC}"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  test <test_path>     Trace a specific test"
    echo "  script <script_path> Trace a Python script"
    echo "  server               Trace FastAPI development server"
    echo "  view <trace_file>    Open trace viewer"
    echo "  list                 List available traces"
    echo ""
    echo "Examples:"
    echo "  $0 test tests/integration/test_diagnostic_flow.py::test_full_session"
    echo "  $0 script scripts/load_curriculum.py"
    echo "  $0 server"
    echo "  $0 view traces/diagnostic_trace.json"
    echo ""
    exit 0
fi

COMMAND=$1
shift

case $COMMAND in
    test)
        if [ -z "$1" ]; then
            echo -e "${YELLOW}Error: Please specify test path${NC}"
            echo "Example: $0 test tests/integration/test_diagnostic_flow.py"
            exit 1
        fi

        TEST_PATH=$1
        TRACE_FILE="$TRACES_DIR/test_trace_$(date +%Y%m%d_%H%M%S).json"

        echo -e "${GREEN}Tracing test: $TEST_PATH${NC}"
        echo -e "${BLUE}Output: $TRACE_FILE${NC}"
        echo ""

        $VIZTRACER \
            --output_file "$TRACE_FILE" \
            --max_stack_depth=15 \
            --ignore_frozen \
            --log_async \
            -m pytest "$TEST_PATH" -v

        echo ""
        echo -e "${GREEN}✅ Trace complete!${NC}"
        echo -e "${BLUE}View: $0 view $TRACE_FILE${NC}"
        ;;

    script)
        if [ -z "$1" ]; then
            echo -e "${YELLOW}Error: Please specify script path${NC}"
            echo "Example: $0 script scripts/load_curriculum.py"
            exit 1
        fi

        SCRIPT_PATH=$1
        TRACE_FILE="$TRACES_DIR/script_trace_$(date +%Y%m%d_%H%M%S).json"

        echo -e "${GREEN}Tracing script: $SCRIPT_PATH${NC}"
        echo -e "${BLUE}Output: $TRACE_FILE${NC}"
        echo ""

        $VIZTRACER \
            --output_file "$TRACE_FILE" \
            --max_stack_depth=15 \
            --ignore_frozen \
            "$SCRIPT_PATH"

        echo ""
        echo -e "${GREEN}✅ Trace complete!${NC}"
        echo -e "${BLUE}View: $0 view $TRACE_FILE${NC}"
        ;;

    server)
        TRACE_FILE="$TRACES_DIR/server_trace_$(date +%Y%m%d_%H%M%S).json"

        echo -e "${GREEN}Tracing FastAPI server${NC}"
        echo -e "${BLUE}Output: $TRACE_FILE${NC}"
        echo ""
        echo -e "${YELLOW}Press Ctrl+C to stop tracing${NC}"
        echo -e "${YELLOW}Make API requests while server is running${NC}"
        echo ""

        $VIZTRACER \
            --output_file "$TRACE_FILE" \
            --max_stack_depth=15 \
            --ignore_frozen \
            --log_async \
            -m uvicorn src.gapsense.main:app --reload --port 8000

        echo ""
        echo -e "${GREEN}✅ Trace complete!${NC}"
        echo -e "${BLUE}View: $0 view $TRACE_FILE${NC}"
        ;;

    view)
        if [ -z "$1" ]; then
            echo -e "${YELLOW}Error: Please specify trace file${NC}"
            echo "Example: $0 view traces/test_trace_20260214_120000.json"
            exit 1
        fi

        TRACE_FILE=$1

        if [ ! -f "$TRACE_FILE" ]; then
            echo -e "${YELLOW}Error: Trace file not found: $TRACE_FILE${NC}"
            exit 1
        fi

        echo -e "${GREEN}Opening trace viewer...${NC}"
        echo -e "${BLUE}Browser will open at http://localhost:9001${NC}"
        echo ""

        $VIZVIEWER "$TRACE_FILE"
        ;;

    list)
        echo -e "${BLUE}Available traces in $TRACES_DIR:${NC}"
        echo ""

        if [ -z "$(ls -A $TRACES_DIR 2>/dev/null)" ]; then
            echo -e "${YELLOW}No traces found${NC}"
            echo ""
            echo "Create a trace with:"
            echo "  $0 test tests/integration/test_diagnostic_flow.py"
        else
            ls -lh "$TRACES_DIR"/*.json 2>/dev/null | awk '{print $9, "(" $5 ")"}'
        fi
        echo ""
        ;;

    *)
        echo -e "${YELLOW}Unknown command: $COMMAND${NC}"
        echo "Run '$0' without arguments for usage"
        exit 1
        ;;
esac
