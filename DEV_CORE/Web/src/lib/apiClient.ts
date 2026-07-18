import { DevCoreApiClient } from "../../../API/clients/typescript/devcore-api-client";

const api = new DevCoreApiClient(process.env.NEXT_PUBLIC_DEVCORE_API_URL ?? "http://localhost:20131");

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
  const url = process.env.NEXT_PUBLIC_DASHBOARD_API_URL ?? "http://localhost:20129";
  const res = await fetch(`${url}/api/dashboard`);
  if (!res.ok) {
    throw new Error(`Dashboard API error: ${res.statusText}`);
  }
  return res.json();
}
