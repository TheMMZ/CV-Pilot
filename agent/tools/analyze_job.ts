import { defineTool } from 'eve/tools';
import { z } from 'zod';
export default defineTool({
 description: 'Analyze a job against the saved local master CV and GitHub evidence. Returns skill coverage and sources; does not submit applications.',
 inputSchema: z.object({title:z.string().min(2),company:z.string().min(1),description:z.string().min(30).max(40000)}),
 async execute(input) {
  const response=await fetch('http://127.0.0.1:4317/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(input),signal:AbortSignal.timeout(10000)});
  if(!response.ok)throw new Error('Start the local CV Pilot workspace with npm run dev before analyzing a job.');
  return response.json();
 }
});
