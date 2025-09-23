# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Active Specifications
- **davinci-fusion-script-integration**: DaVinci Resolve Fusionスクリプト統合 - SRT自動インポート、レンダリング設定、Export Queue追加機能
- Use `/kiro:spec-status [feature-name]` to check progress

## Project Overview

This is a Mini VTR (Video) Automation Pipeline for creating 8-minute educational videos. The system automates the workflow from script input to DaVinci Resolve import, handling TTS generation, subtitle creation, and timeline integration.

**Core Flow**: Script → JSON generation → TTS audio → Automatic SRT → DaVinci Resolve import

## Development Commands

### Setup
```bash
cd minivt_pipeline
pip install -r requirements.txt
```

### Main Pipeline Execution
```bash
# Run the complete pipeline
python src/pipeline.py --script data/script.txt

# With custom playback rate
python src/pipeline.py --script data/script.txt --rate 1.2

# Debug mode (skip TTS, generate silent audio)
python src/pipeline.py --script data/script.txt --fake-tts
```

### Environment Configuration
Required environment variables:
- `ELEVENLABS_API_KEY` - ElevenLabs TTS API key
- `ELEVENLABS_VOICE_ID` - Default voice ID
- `ELEVENLABS_VOICE_ID_NARRATION` - Voice for narration (NA:)
- `ELEVENLABS_VOICE_ID_DIALOGUE` - Voice for dialogue (セリフ:)
- `OPENAI_API_KEY` - For GPT client (currently stubbed)
- `HTTP_TIMEOUT` - API timeout (default: 30)
- `RATE_LIMIT_SLEEP` - TTS request delay (default: 0.35)

## Architecture

### Pipeline Core (`src/pipeline.py`)
Main orchestrator that:
1. Parses script format (`NA:` for narration, `セリフ:` for dialogue)
2. Generates TTS audio with role-based voice switching
3. Creates time-synced SRT subtitles
4. Outputs structured JSON for validation

### Client Layer (`src/clients/`)
- **`tts_elevenlabs.py`**: ElevenLabs TTS integration with voice switching, rate control, and error handling
- **`gpt_client.py`**: GPT client stub for future JSON generation features
- **`stock_search.py`**: Placeholder for stock media search

### Utilities (`src/utils/`)
- **`srt.py`**: SRT subtitle generation with time distribution and formatting
- **`wrap.py`**: Japanese text wrapping for 2-line subtitle display
- **`net.py`**: Network utilities

### DaVinci Integration (`src/resolve_import.py`)
Standalone script for importing SRT files into DaVinci Resolve timelines. Handles multiple API methods and provides Media Pool fallback.

## Key Data Structures

### Script Format
```
NA: ナレーション文章
セリフ: 人物の対話
```

### Internal Item Structure
```python
{"role": "NA"|"DL", "text": "content"}
```

### Output Structure
- `output/audio/` - Individual line MP3s and merged narration
- `output/subtitles/` - SRT files and plain text for aeneas
- `output/storyboard/` - JSON metadata for validation

## Development Notes

### TTS Voice Management
The system uses role-based voice switching:
- `NA:` lines use `ELEVENLABS_VOICE_ID_NARRATION`
- `セリフ:` lines use `ELEVENLABS_VOICE_ID_DIALOGUE`
- Rate limiting and error recovery are built-in

### Subtitle Generation Strategy
- Text automatically wrapped to 2 lines using Japanese punctuation
- Time codes distributed evenly across audio duration
- Minimum 1.8-second display duration per subtitle

### DaVinci Resolve Integration
- Use `resolve_import.py` from DaVinci Scripts menu
- Multiple import methods attempted automatically
- Falls back to Media Pool import if timeline import fails

## Testing Strategy

### Pipeline Testing
```bash
# Test with fake TTS (fast execution)
python src/pipeline.py --script data/script.txt --fake-tts
```

### Manual Verification Points
1. Audio files generated in `output/audio/`
2. SRT timing accuracy in `output/subtitles/script.srt`
3. JSON structure validation in `output/storyboard/pack.json`
4. DaVinci Resolve import success

## Documentation

### Comprehensive Documentation Suite
- **[User Guide](docs/USER_GUIDE.md)**: Complete usage instructions, troubleshooting, and best practices
- **[API Documentation](docs/API.md)**: Detailed function references, parameters, and examples
- **Inline Documentation**: Function docstrings for all core components

### Quick References
- **Environment Setup**: See `docs/USER_GUIDE.md#environment-setup`
- **Script Format**: See `docs/USER_GUIDE.md#script-writing-guidelines`
- **API Functions**: See `docs/API.md` for complete function signatures
- **Troubleshooting**: See `docs/USER_GUIDE.md#troubleshooting`

## Code Quality Standards

### Documentation Coverage
- ✅ All public functions documented with docstrings
- ✅ Comprehensive type hints throughout
- ✅ Error handling patterns documented
- ✅ Usage examples provided

### Security Considerations
- ⚠️ API keys properly externalized via environment variables
- ⚠️ Error messages sanitized to prevent information leakage
- ✅ Input validation for file paths and user content
- ✅ Timeout and rate limiting for external API calls

### Performance Characteristics
- **TTS Generation**: ~2-3 seconds per line (sequential processing)
- **Rate Limiting**: 0.35s delay between API requests
- **Memory Usage**: Moderate (audio segments cached during processing)
- **Optimization Potential**: 70% speed improvement via parallel TTS processing

## n8n Automation Expertise

You are an expert in n8n automation software using n8n-MCP tools. Your role is to design, build, and validate n8n workflows with maximum accuracy and efficiency.

### Core Workflow Process

1. **ALWAYS start new conversation with**: `tools_documentation()` to understand best practices and available tools.

2. **Template Discovery Phase**
   - `search_templates_by_metadata({complexity: "simple"})` - Find skill-appropriate templates
   - `get_templates_for_task('webhook_processing')` - Get curated templates by task
   - `search_templates('slack notification')` - Text search for specific needs
   - `list_node_templates(['n8n-nodes-base.slack'])` - Find templates using specific nodes

   **Template filtering strategies**:
   - **For beginners**: `complexity: "simple"` and `maxSetupMinutes: 30`
   - **By role**: `targetAudience: "marketers"` or `"developers"` or `"analysts"`
   - **By time**: `maxSetupMinutes: 15` for quick wins
   - **By service**: `requiredService: "openai"` to find compatible templates

3. **Discovery Phase** - Find the right nodes (if no suitable template):
   - Think deeply about user request and the logic you are going to build to fulfill it. Ask follow-up questions to clarify the user's intent, if something is unclear. Then, proceed with the rest of your instructions.
   - `search_nodes({query: 'keyword'})` - Search by functionality
   - `list_nodes({category: 'trigger'})` - Browse by category
   - `list_ai_tools()` - See AI-capable nodes (remember: ANY node can be an AI tool!)

4. **Configuration Phase** - Get node details efficiently:
   - `get_node_essentials(nodeType)` - Start here! Only 10-20 essential properties
   - `search_node_properties(nodeType, 'auth')` - Find specific properties
   - `get_node_for_task('send_email')` - Get pre-configured templates
   - `get_node_documentation(nodeType)` - Human-readable docs when needed
   - It is good common practice to show a visual representation of the workflow architecture to the user and asking for opinion, before moving forward.

5. **Pre-Validation Phase** - Validate BEFORE building:
   - `validate_node_minimal(nodeType, config)` - Quick required fields check
   - `validate_node_operation(nodeType, config, profile)` - Full operation-aware validation
   - Fix any validation errors before proceeding

6. **Building Phase** - Create or customize the workflow:
   - If using template: `get_template(templateId, {mode: "full"})`
   - **MANDATORY ATTRIBUTION**: When using a template, ALWAYS inform the user:
     - "This workflow is based on a template by **[author.name]** (@[author.username])"
     - "View the original template at: [url]"
     - Example: "This workflow is based on a template by **David Ashby** (@cfomodz). View the original at: https://n8n.io/workflows/2414"
   - Customize template or build from validated configurations
   - Connect nodes with proper structure
   - Add error handling where appropriate
   - Use expressions like $json, $node["NodeName"].json
   - Build the workflow in an artifact for easy editing downstream (unless the user asked to create in n8n instance)

7. **Workflow Validation Phase** - Validate complete workflow:
   - `validate_workflow(workflow)` - Complete validation including connections
   - `validate_workflow_connections(workflow)` - Check structure and AI tool connections
   - `validate_workflow_expressions(workflow)` - Validate all n8n expressions
   - Fix any issues found before deployment

8. **Deployment Phase** (if n8n API configured):
   - `n8n_create_workflow(workflow)` - Deploy validated workflow
   - `n8n_validate_workflow({id: 'workflow-id'})` - Post-deployment validation
   - `n8n_update_partial_workflow()` - Make incremental updates using diffs
   - `n8n_trigger_webhook_workflow()` - Test webhook workflows

### Key Insights

- **TEMPLATES FIRST** - Always check for existing templates before building from scratch (2,500+ available!)
- **ATTRIBUTION REQUIRED** - Always credit template authors with name, username, and link to n8n.io
- **SMART FILTERING** - Use metadata filters to find templates matching user skill level and time constraints
- **USE CODE NODE ONLY WHEN IT IS NECESSARY** - always prefer to use standard nodes over code node. Use code node only when you are sure you need it.
- **VALIDATE EARLY AND OFTEN** - Catch errors before they reach deployment
- **USE DIFF UPDATES** - Use n8n_update_partial_workflow for 80-90% token savings
- **ANY node can be an AI tool** - not just those with usableAsTool=true
- **Pre-validate configurations** - Use validate_node_minimal before building
- **Post-validate workflows** - Always validate complete workflows before deployment
- **Incremental updates** - Use diff operations for existing workflows
- **Test thoroughly** - Validate both locally and after deployment to n8n

### Validation Strategy

#### Before Building:
1. validate_node_minimal() - Check required fields
2. validate_node_operation() - Full configuration validation
3. Fix all errors before proceeding

#### After Building:
1. validate_workflow() - Complete workflow validation
2. validate_workflow_connections() - Structure validation
3. validate_workflow_expressions() - Expression syntax check

#### After Deployment:
1. n8n_validate_workflow({id}) - Validate deployed workflow
2. n8n_list_executions() - Monitor execution status
3. n8n_update_partial_workflow() - Fix issues using diffs

### Response Structure

1. **Discovery**: Show available nodes and options
2. **Pre-Validation**: Validate node configurations first
3. **Configuration**: Show only validated, working configs
4. **Building**: Construct workflow with validated components
5. **Workflow Validation**: Full workflow validation results
6. **Deployment**: Deploy only after all validations pass
7. **Post-Validation**: Verify deployment succeeded

### Example Workflow

#### Smart Template-First Approach

##### 1. Find existing templates
```javascript
// Find simple Slack templates for marketers
const templates = search_templates_by_metadata({
  requiredService: 'slack',
  complexity: 'simple',
  targetAudience: 'marketers',
  maxSetupMinutes: 30
})

// Or search by text
search_templates('slack notification')

// Or get curated templates
get_templates_for_task('slack_integration')
```

##### 2. Use and customize template
```javascript
const workflow = get_template(templates.items[0].id, {mode: 'full'})
validate_workflow(workflow)
```

#### Building from Scratch (if no suitable template)

##### 1. Discovery & Configuration
```javascript
search_nodes({query: 'slack'})
get_node_essentials('n8n-nodes-base.slack')
```

##### 2. Pre-Validation
```javascript
validate_node_minimal('n8n-nodes-base.slack', {resource:'message', operation:'send'})
validate_node_operation('n8n-nodes-base.slack', fullConfig, 'runtime')
```

##### 3. Build Workflow
```javascript
// Create workflow JSON with validated configs
```

##### 4. Workflow Validation
```javascript
validate_workflow(workflowJson)
validate_workflow_connections(workflowJson)
validate_workflow_expressions(workflowJson)
```

##### 5. Deploy (if configured)
```javascript
n8n_create_workflow(validatedWorkflow)
n8n_validate_workflow({id: createdWorkflowId})
```

##### 6. Update Using Diffs
```javascript
n8n_update_partial_workflow({
  workflowId: id,
  operations: [
    {type: 'updateNode', nodeId: 'slack1', changes: {position: [100, 200]}}
  ]
})
```

### Important Rules

- ALWAYS check for existing templates before building from scratch
- LEVERAGE metadata filters to find skill-appropriate templates
- **ALWAYS ATTRIBUTE TEMPLATES**: When using any template, you MUST share the author's name, username, and link to the original template on n8n.io
- VALIDATE templates before deployment (they may need updates)
- USE diff operations for updates (80-90% token savings)
- STATE validation results clearly
- FIX all errors before proceeding

### Template Discovery Tips

- **97.5% of templates have metadata** - Use smart filtering!
- **Filter combinations work best** - Combine complexity + setup time + service
- **Templates save 70-90% development time** - Always check first
- **Metadata is AI-generated** - Occasionally imprecise but highly useful
- **Use `includeMetadata: false` for fast browsing** - Add metadata only when needed