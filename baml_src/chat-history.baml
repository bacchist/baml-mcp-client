class ChatMessage {
  role "user" | "assistant"
  content string
}

class ChatResponse {
  content string
}

class MCPTool {
  name string
  description string
  input_schema string
}

class ToolCall {
  name string
  args string @description("The arguments to pass to the tool. Must be a valid JSON object.")
}

function ChatWithLLM(messages: ChatMessage[], available_tools: MCPTool[]) -> ChatResponse | ToolCall {
  client CustomGPT4oMini
  prompt #"
    You are a helpful assistant with access to these tools:
    {% for tool in available_tools %}
    - Name: {{ tool.name }}
      Description: {{ tool.description }}
      Parameters: {{ tool.input_schema }}
    {% endfor %}

    When you need to use a tool, respond with a ToolCall.

    {{ ctx.output_format }}

    Chat history:
    {% for message in messages %}
      {{ _.role(message.role) }} 
      {{ message.content }}
    {% endfor %}
  "#
}

test TestName {
  functions [ChatWithLLM]
  args {
    messages [
      {
        role "user"
        content "Hello!"
      }
      {
        role "assistant"
        content "Hi!"
      }
      {
        role "user"
        content "get_forecast for Montgomery Village, MD"
      }
    ]
    available_tools [
      {
        name "get_alerts"
        description "Get weather alerts for a US state."
        input_schema "{\"properties\": {\"state\": {\"title\": \"State\", \"type\": \"string\"}}, \"required\": [\"state\"], \"title\": \"get_alertsArguments\", \"type\": \"object\"}"
      }
      {
        name "get_forecast"
        description "Get the weather forecast for a location."
        input_schema "{\"properties\": {\"latitude\": {\"title\": \"Latitude\", \"type\": \"number\"}, \"longitude\": {\"title\": \"Longitude\", \"type\": \"number\"}}, \"required\": [\"latitude\", \"longitude\"], \"title\": \"get_forecastArguments\", \"type\": \"object\"}"
      }
    ]
  }
}

