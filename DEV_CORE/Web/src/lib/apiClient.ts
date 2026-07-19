import { DevCoreApiClient } from "../../../API/clients/typescript/devcore-api-client";

// Use the Next.js rewrite proxy so the browser never makes cross-origin requests.
// All calls go to localhost:3000/proxy/… and Next.js forwards them server-side.
const api = new DevCoreApiClient("/proxy");

export async function getHealth() {
  return api.health();
}

export async function getTasks(project = "devcore") {
  return api.tasks(project);
}

export async function getWorkflows() {
  return api.listWorkflows();
}

export async function getDashboard() {
  const res = await fetch("/proxy/dashboard/dashboard");
  if (!res.ok) {
    throw new Error(`Dashboard API error: ${res.statusText}`);
  }
  return res.json();
}

