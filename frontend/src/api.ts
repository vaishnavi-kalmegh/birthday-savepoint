export type CapsuleSummary={id?:string;year:number;state:"sealed"|"available"|"opened";unlock_at:string;content_type?:string};
export type Capsule={id:string;year:number;content_type:string;body:{title?:string;text:string};opened_at:string|null};
export type Profile={display_name:string;theme:Record<string,unknown>;is_admin?:boolean};
let csrfToken="";
async function request<T>(path:string,init:RequestInit={}):Promise<T>{const headers=new Headers(init.headers);if(init.body&&!headers.has("Content-Type"))headers.set("Content-Type","application/json");if(init.method&&!["GET","HEAD","OPTIONS"].includes(init.method.toUpperCase())&&csrfToken)headers.set("X-CSRF-Token",csrfToken);const response=await fetch(path,{...init,headers,credentials:"same-origin"});if(!response.ok){if(response.status===401)csrfToken="";const body=await response.json().catch(()=>({}));throw new Error(typeof body.detail==="string"?body.detail:"Something went wrong. Try again.");}return response.json() as Promise<T>}
export async function login(loginId:string,password:string){const result=await request<{csrf_token:string}>("/api/auth/login",{method:"POST",body:JSON.stringify({login_id:loginId,password})});csrfToken=result.csrf_token}
export async function restoreSession(){const result=await request<{csrf_token:string}>("/api/auth/csrf",{method:"POST"});csrfToken=result.csrf_token;return request<Profile>("/api/auth/me")}
export async function getCapsules(){return request<CapsuleSummary[]>("/api/capsules")}
export async function getCapsule(id:string){return request<Capsule>("/api/capsules/"+encodeURIComponent(id))}
export async function openCapsule(id:string){await request("/api/capsules/"+encodeURIComponent(id)+"/open",{method:"POST"})}
export async function createFriend(input:{login_id:string;password:string;display_name:string;birth_month:number;birth_day:number;timezone:string;theme:{scene:string}}){return request<{public_id:string}>("/api/admin/friends",{method:"POST",body:JSON.stringify(input)})}
export async function createLetter(publicId:string,input:{year:number;content_type:"letter";body:{title:string;text:string};published:boolean}){return request<{id:string}>(`/api/admin/friends/${encodeURIComponent(publicId)}/capsules`,{method:"POST",body:JSON.stringify(input)})}
export async function logout(){try{await request("/api/auth/logout",{method:"POST"})}finally{csrfToken=""}}