export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization, Accept',
    };
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }
    if (url.pathname === '/' && request.method === 'GET') {
      return new Response(JSON.stringify({ message: 'AI Check MCP Server is running', status: 'ok' }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }
    if (url.pathname === '/mcp') {
      if (request.method === 'GET') {
        const encoder = new TextEncoder();
        const stream = new ReadableStream({
          start(controller) {
            controller.enqueue(encoder.encode('event: message\ndata: {"jsonrpc":"2.0","method":"notifications/initialized"}\n\n'));
            const heartbeat = setInterval(() => {
              controller.enqueue(encoder.encode(': ping\n\n'));
            }, 15000);
            request.signal.addEventListener('abort', () => {
              clearInterval(heartbeat);
              controller.close();
            });
          }
        });
        return new Response(stream, {
          headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', ...corsHeaders }
        });
      }
      if (request.method === 'POST') {
        try {
          const body = await request.json();
          const result = await handleMcp(body, env);
          const accept = request.headers.get('Accept') || '';
          if (accept.includes('text/event-stream')) {
            return new Response(`event: message\ndata: ${JSON.stringify(result)}\n\n`, {
              headers: { 'Content-Type': 'text/event-stream', ...corsHeaders }
            });
          }
          return new Response(JSON.stringify(result), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        } catch (e) {
          return new Response(JSON.stringify({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error' } }), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        }
      }
    }
    return new Response('Not Found', { status: 404, headers: corsHeaders });
  }
};

async function handleMcp(body, env) {
  const method = body.method || '';
  const id = body.id;
  try {
    if (method === 'initialize') {
      return { jsonrpc: '2.0', id, result: {
        protocolVersion: '2025-03-26',
        capabilities: { tools: {} },
        serverInfo: { name: 'ai-check-mcp', version: '1.0.0' }
      }};
    }
    if (method === 'notifications/initialized' || method === 'ping') {
      return { jsonrpc: '2.0', id, result: {} };
    }
    if (method === 'tools/list') {
      return { jsonrpc: '2.0', id, result: { tools: [
        { name: 'query_activity', description: '查询用户过去N天的手机活动摘要', inputSchema: {
          type: 'object', properties: { days: { type: 'integer', description: '查询天数（默认1天）' } } } },
        { name: 'send_notification', description: '给用户手机发送一条推送通知', inputSchema: {
          type: 'object', properties: {
            title: { type: 'string', description: '通知标题' },
            message: { type: 'string', description: '通知内容' },
            priority: { type: 'integer', description: '优先级1-5，默认3' }
          }, required: ['title', 'message'] } }
      ]}};
    }
    if (method === 'tools/call') {
      const params = body.params || {};
      const name = params.name;
      const args = params.arguments || {};
      if (name === 'query_activity') {
        const days = args.days || 1;
        const data = await queryActivity(days, env);
        return { jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: JSON.stringify(data) }] } };
      }
      if (name === 'send_notification') {
        const ok = await sendNtfy(args.title || '通知', args.message || '', args.priority || 3, env);
        return { jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: ok ? '通知发送成功' : '通知发送失败' }] } };
      }
      return { jsonrpc: '2.0', id, error: { code: -32602, message: '未知工具: ' + name } };
    }
    return { jsonrpc: '2.0', id, error: { code: -32601, message: '未知方法: ' + method } };
  } catch (e) {
    return { jsonrpc: '2.0', id, error: { code: -32603, message: 'Internal error' } };
  }
}

async function queryActivity(days, env) {
  const api = env.ORIGIN_API || 'https://web-production-5c189.up.railway.app';
  const token = env.AUTH_TOKEN || 'Jh3k9xQw2mPv8LzT5nYc';
  try {
    const resp = await fetch(`${api}/activity/summary?days=${days}`, { headers: { 'Authorization': 'Bearer ' + token } });
    return resp.ok ? await resp.json() : { error: await resp.text() };
  } catch (e) {
    return { error: e.message };
  }
}

async function sendNtfy(title, message, priority, env) {
  const topic = env.NTFY_TOPIC || 'jamesjuhoon';
  try {
    const resp = await fetch('https://ntfy.sh/' + topic, {
      method: 'POST',
      body: message,
      headers: { 'Title': title, 'Priority': String(priority), 'Tags': 'mobile_phone' }
    });
    return resp.ok;
  } catch (e) {
    return false;
  }
}
