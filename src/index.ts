#!/usr/bin/env node
import { createInterface } from 'readline';

interface JsonRpcRequest {
  jsonrpc: '2.0';
  id: number;
  method: string;
  params?: any;
}

interface JsonRpcResponse {
  jsonrpc: '2.0';
  id: number;
  result?: any;
  error?: {
    code: number;
    message: string;
  };
}

// Server definition
class MCPServer {
  private tools = {
    hello_world: {
      description: 'A simple hello world function',
      parameters: {
        type: 'object',
        properties: {
          name: {
            type: 'string',
            description: 'Name to say hello to'
          }
        },
        required: ['name']
      }
    }
  };

  async handleRequest(request: JsonRpcRequest): Promise<JsonRpcResponse> {
    try {
      if (request.method === 'initialize') {
        return {
          jsonrpc: '2.0',
          id: request.id,
          result: {
            capabilities: {
              tools: this.tools
            }
          }
        };
      }

      if (request.method === 'callTool') {
        const { name, arguments: args } = request.params;
        if (name === 'hello_world') {
          return {
            jsonrpc: '2.0',
            id: request.id,
            result: {
              content: [{
                type: 'text',
                text: `Hello, ${args.name}!`
              }]
            }
          };
        }
      }

      return {
        jsonrpc: '2.0',
        id: request.id,
        error: {
          code: -32601,
          message: 'Method not found'
        }
      };
    } catch (error) {
      return {
        jsonrpc: '2.0',
        id: request.id,
        error: {
          code: -32000,
          message: error instanceof Error ? error.message : 'Unknown error'
        }
      };
    }
  }
}

// Initialize server
const server = new MCPServer();

// Set up stdin/stdout interface
const rl = createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

// Handle incoming messages
rl.on('line', async (line) => {
  try {
    const request = JSON.parse(line);
    const response = await server.handleRequest(request);
    console.log(JSON.stringify(response));
  } catch (error) {
    console.error('Error:', error instanceof Error ? error.message : String(error));
  }
});

// Handle shutdown
const cleanup = () => {
  console.error('Shutting down...');
  rl.close();
  process.exit(0);
};

process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);

console.error('MCP Server started, waiting for messages...');
