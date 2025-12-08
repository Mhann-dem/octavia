export async function apiClient(endpoint: string, options: RequestInit = {}) {
  const baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
  const fullUrl = `${baseUrl}${endpoint}`;

  const defaultHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };

  const session = document.cookie.match(/octavia_session=([^;]+)/)?.[1];
  if (session) {
    defaultHeaders["Cookie"] = `octavia_session=${session}`;
  }

  const response = await fetch(fullUrl, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.message || response.statusText);
  }

  return response.json();
}
