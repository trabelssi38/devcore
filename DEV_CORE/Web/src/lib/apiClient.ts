import { DevCoreApiClient } from "../../../API/clients/typescript/devcore-api-client";

const api = new DevCoreApiClient(process.env.NEXT_PUBLIC_DEVCORE_API_URL ?? "");

export async function getHealth() {
  return api.health();
}

export async function getTasks(project = "devcore") {
  return api.tasks(project);
}
