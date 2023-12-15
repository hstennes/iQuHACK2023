// Next.js API route support: https://nextjs.org/docs/api-routes/introduction
import type { NextApiRequest, NextApiResponse } from 'next'

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const result = await fetch(`http://localhost:5000/query/submit/${req.query["query"]}`);
  if (result.ok)
    res.status(200).send(await result.json())
  else
    res.status(500).send(result.statusText);
}
