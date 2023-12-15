import { ReactNode, useState, useEffect } from "react";
import useSWR from "swr";
import { mutate } from "swr";
import { useRouter } from "next/router";

interface Props {
  query: string;
}

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function ResultsData(props: Props) {
  const [id, setId] = useState("");

  const { data, error, isLoading } = useSWR(
    id == ""
      ? `/api/query/submit?query=${props.query}`
      : `/api/query/status?id=${id}`,
    fetcher,
    { revalidateOnFocus: false, revalidateOnReconnect: false }
  );

  useEffect(() => {
    if (isLoading || error) return;

    if (id == "") {
      setId(data["id"]);
      return;
    }

    if (data["done"]) return;

    const interval = setInterval(() => {
      // Requery status
      mutate(
        (key) => typeof key === "string" && key.startsWith("/api/query/status"),
        undefined,
        { revalidate: true }
      );
    }, 3000);

    return () => clearInterval(interval);
  }, [id, isLoading, data, error]);

  if (error)
    return (
      <div>
        {id == ""
          ? "Failed to submit request"
          : "Failed to query request status"}
      </div>
    );
  if (isLoading || id == "" || !data["done"])
    return (
      <div>{id == "" ? "Creating request..." : "Waiting for request..."}</div>
    );

  let sentSum = 0;
  let scoreSum = 0;
  data["data"].forEach((entry: any) => {
    sentSum += entry["sentiment"];
    scoreSum += entry["score"];
  });

  let average_sentiment = sentSum / scoreSum;
  let average_sentiment_percent = Math.round((average_sentiment + 1) * 50);
  return (
    <>
      <div className="pt-14 w-full px-24">
        <div className="w-full bg-gray-200 rounded-full dark:bg-gray-700">
          <div
            className="bg-gradient-to-tl from-[#FF71BE] via-[#B871FF] to-[#3183FF] text-xs font-lg text-blue-100 text-center p-0.5 py-6 leading-none rounded-full"
            style={{ width: `${average_sentiment_percent}%` }}
          ></div>
        </div>
        <div
          className={"relative"}
          style={{ marginLeft: `calc(${average_sentiment_percent}% - 20px)` }}
        >
          <div className="absolute bg-gray-300 h-8 w-8 rounded-sm rotate-45"></div>
          <div className="relative top-2 right-12 bg-gray-300 h-14 w-32 rounded-lg flex items-center justify-center">
            <h2 className="text-black font-semibold">
              {average_sentiment_percent}% positive
            </h2>
          </div>
        </div>
      </div>
      <h2 className="mt-12 mb-8 text-center text-4xl font-medium">
        Keyword Analysis
      </h2>
      <ul>
        {data["data"].map((entry: any) => (
          <li className="text-2xl py-4">
            {entry["key"]}{" "}
            <span className="font-bitcount ml-8">
              <span className="bg-gradient-to-tr from-[#FF71BE] via-[#B871FF] to-[#3183FF] bg-clip-text text-transparent font-bold">
                {Math.round((entry["sentiment"] / entry["score"] + 1) * 50)}%
              </span>{" "}
              positive
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}
