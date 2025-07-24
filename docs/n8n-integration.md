# N8N Integration Guide

This guide shows how to integrate the Proxmox MCP Server with N8N for workflow automation.

## Prerequisites

- N8N instance running and accessible
- Proxmox MCP Server deployed and running
- Basic understanding of N8N workflows

## Server URLs

- **Docker**: http://localhost:8000 or http://docker-host-ip:8000
- **LXC**: http://172.32.0.200:8000

## Basic N8N Workflow Setup

### 1. HTTP Request Node Configuration

Add an HTTP Request node to your workflow:

**Settings**:
- **Method**: GET/POST (depending on endpoint)
- **URL**: `http://172.32.0.200:8000/proxmox/nodes` (adjust for your deployment)
- **Headers**: 
  ```json
  {
    "Content-Type": "application/json"
  }
  ```

### 2. Common Endpoints for N8N

#### Get Proxmox Nodes
```
GET http://172.32.0.200:8000/proxmox/nodes
```

#### Get VMs for a Node
```
GET http://172.32.0.200:8000/proxmox/node/{node_name}/vms
```

#### Get Available Ollama Models
```
GET http://172.32.0.200:8000/ollama/models
```

#### Generate AI Response
```
POST http://172.32.0.200:8000/ollama/generate
Content-Type: application/json

{
  "model": "llama2",
  "prompt": "Analyze this Proxmox infrastructure",
  "stream": false
}
```

## Example Workflows

### 1. Infrastructure Monitoring Workflow

**Purpose**: Monitor Proxmox VMs and send alerts

**Nodes**:
1. **Schedule Trigger** (every 5 minutes)
2. **HTTP Request** - Get all nodes
3. **HTTP Request** - Get VMs for each node
4. **Function** - Process VM data
5. **IF** - Check for issues
6. **Send Email** - Alert if problems found

**Function Node Code**:
```javascript
// Process VM data and check for issues
const vms = items[0].json.vms;
const issues = [];

for (const vm of vms) {
  if (vm.status !== 'running' && vm.template !== 1) {
    issues.push({
      vmid: vm.vmid,
      name: vm.name,
      status: vm.status,
      node: vm.node
    });
  }
}

return [{
  json: {
    issues: issues,
    hasIssues: issues.length > 0
  }
}];
```

### 2. AI-Powered Infrastructure Analysis

**Purpose**: Use AI to analyze infrastructure and provide recommendations

**Nodes**:
1. **Manual Trigger**
2. **HTTP Request** - Get infrastructure data
3. **Function** - Format data for AI
4. **HTTP Request** - Send to Ollama for analysis
5. **Function** - Process AI response
6. **Send to Slack/Email** - Share recommendations

**AI Prompt Function**:
```javascript
// Format infrastructure data for AI analysis
const nodes = items[0].json.nodes;
const prompt = `
Analyze this Proxmox infrastructure and provide recommendations:

Infrastructure Data:
${JSON.stringify(nodes, null, 2)}

Please provide:
1. Resource utilization assessment
2. Potential optimization opportunities
3. Security recommendations
4. Capacity planning suggestions
`;

return [{
  json: {
    model: "llama2",
    prompt: prompt,
    stream: false
  }
}];
```

### 3. Automated VM Management

**Purpose**: Automatically manage VMs based on conditions

**Nodes**:
1. **Webhook Trigger**
2. **HTTP Request** - Get VM status
3. **Switch** - Route based on action
4. **HTTP Request** - Execute VM operations
5. **Function** - Log results

## Advanced Integration Patterns

### 1. Error Handling

Add error handling to your workflows:

```javascript
// Error handling in Function node
try {
  const response = items[0].json;
  if (response.error) {
    throw new Error(`API Error: ${response.error}`);
  }
  return items;
} catch (error) {
  return [{
    json: {
      error: error.message,
      timestamp: new Date().toISOString()
    }
  }];
}
```

### 2. Data Transformation

Transform Proxmox data for other systems:

```javascript
// Transform VM data for external systems
const vms = items[0].json.vms;
const transformed = vms.map(vm => ({
  id: vm.vmid,
  name: vm.name,
  status: vm.status,
  memory_mb: vm.maxmem / 1024 / 1024,
  cpu_cores: vm.cpus,
  uptime_hours: vm.uptime / 3600,
  node: vm.node
}));

return [{
  json: {
    virtual_machines: transformed,
    count: transformed.length,
    timestamp: new Date().toISOString()
  }
}];
```

### 3. Conditional Logic

Implement business logic in workflows:

```javascript
// Conditional VM management
const vm = items[0].json;
const cpuThreshold = 80;
const memoryThreshold = 90;

let action = 'none';
let reason = '';

if (vm.cpu_usage > cpuThreshold) {
  action = 'scale_up';
  reason = `CPU usage ${vm.cpu_usage}% exceeds threshold`;
} else if (vm.memory_usage > memoryThreshold) {
  action = 'scale_up';
  reason = `Memory usage ${vm.memory_usage}% exceeds threshold`;
} else if (vm.cpu_usage < 20 && vm.memory_usage < 30) {
  action = 'scale_down';
  reason = 'Low resource utilization detected';
}

return [{
  json: {
    vmid: vm.vmid,
    action: action,
    reason: reason,
    timestamp: new Date().toISOString()
  }
}];
```

## Best Practices

### 1. Connection Management
- Use connection pooling for frequent requests
- Implement retry logic for failed requests
- Set appropriate timeouts

### 2. Security
- Use HTTPS in production environments
- Implement authentication if required
- Sanitize data before sending to external systems

### 3. Performance
- Batch API calls when possible
- Use caching for frequently accessed data
- Implement rate limiting

### 4. Monitoring
- Log all API interactions
- Set up alerts for failed workflows
- Monitor resource usage

## Troubleshooting N8N Integration

### Common Issues

1. **Connection Timeout**
   - Check if MCP server is running
   - Verify network connectivity
   - Increase timeout in HTTP Request node

2. **Authentication Errors**
   - Verify server configuration
   - Check if authentication is required

3. **Data Format Issues**
   - Use Function nodes to debug data flow
   - Check API response format
   - Validate JSON structure

### Debug Tips

1. **Enable N8N Debug Mode**:
   ```bash
   export N8N_LOG_LEVEL=debug
   ```

2. **Use Function Nodes for Debugging**:
   ```javascript
   console.log('Debug data:', JSON.stringify(items, null, 2));
   return items;
   ```

3. **Test API Endpoints Manually**:
   ```bash
   curl -X GET http://172.32.0.200:8000/health
   ```

## Example Workflow Files

Check the `/examples/n8n-workflows/` directory for complete workflow JSON files that you can import directly into N8N.
