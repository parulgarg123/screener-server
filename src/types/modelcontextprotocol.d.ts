declare module '@modelcontextprotocol/sdk' {
  export interface ToolDefinition {
    description: string;
    parameters: {
      type: string;
      properties: Record<string, {
        type: string;
        description: string;
      }>;
      required: string[];
    };
  }

  export interface ToolCallResult {
    content: Array<{
      type: string;
      text: string;
    }>;
  }

  export interface McpServerOptions {
    tools: Record<string, ToolDefinition>;
    onToolCall: (tool: string, args: unknown) => Promise<ToolCallResult>;
  }

  export class McpServer {
    constructor(options: McpServerOptions);
    handleRequest(message: unknown): Promise<unknown>;
  }
}
