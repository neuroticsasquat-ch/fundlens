import { Anchor, Code, Stack, Table, Text, Typography } from "@mantine/core";
import type { ReactNode } from "react";
import Markdown from "react-markdown";
import type { Components } from "react-markdown";
import { Link } from "react-router";
import { $api, type Meta } from "../api/client";
import QueryStatus from "../components/QueryStatus";
import { count, DASH, isoDate, percent } from "../components/format";
import { usePageTitle } from "../components/usePageTitle";
import methodology from "../content/methodology.md?raw";

const REPO = "https://github.com/neuroticsasquat-ch/fundlens";

// A line of the content that is only `{{name}}` is where the live build's figures go.
const SLOT = /^\{\{(\w+)\}\}$/m;

const SLOTS: Record<string, (meta: Meta) => ReactNode> = {
  cycles: (meta) => <Cycles meta={meta} />,
  quality: (meta) => <Quality meta={meta} />,
};

// The content's own links: a path stays inside the app, anything else is a plain link.
const components: Components = {
  a: ({ href = "", children }) =>
    href.startsWith("/") ? (
      <Anchor component={Link} to={href}>
        {children}
      </Anchor>
    ) : (
      <Anchor href={href}>{children}</Anchor>
    ),
};

/** The cycles the live build holds, each with the dates its FEC files were downloaded. */
function Cycles({ meta }: { meta: Meta }) {
  const cycles = Object.entries(meta.cycles).sort(([a], [b]) => Number(b) - Number(a));
  if (cycles.length === 0) return <Text>No cycle is published yet.</Text>;
  return (
    <Table withTableBorder>
      <Table.Thead>
        <Table.Tr>
          <Table.Th>Cycle</Table.Th>
          <Table.Th>FEC files downloaded</Table.Th>
          <Table.Th>Build</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {cycles.map(([cycle, { build_id, source_dates }]) => {
          const dates = [...new Set(Object.values(source_dates))].sort();
          return (
            <Table.Tr key={cycle}>
              <Table.Td>{cycle}</Table.Td>
              <Table.Td>
                {dates.length > 1
                  ? `${isoDate(dates[0])} to ${isoDate(dates.at(-1))}`
                  : isoDate(dates[0])}
              </Table.Td>
              <Table.Td>
                <Code>{build_id}</Code>
              </Table.Td>
            </Table.Tr>
          );
        })}
      </Table.Tbody>
    </Table>
  );
}

/** The live build's precision and recall against DIME, and what its resolution applied. */
function Quality({ meta }: { meta: Meta }) {
  const scored = meta.precision != null;
  return (
    <Stack gap="sm">
      {scored ? (
        <>
          <Table withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Scope</Table.Th>
                <Table.Th>Precision</Table.Th>
                <Table.Th>Recall</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              <Table.Tr>
                <Table.Td>Everyone matched to DIME</Table.Td>
                <Table.Td>{percent(meta.precision)}</Table.Td>
                <Table.Td>{percent(meta.recall)}</Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Td>The 10,000 who gave the most matched dollars</Table.Td>
                <Table.Td>{percent(meta.precision_top)}</Table.Td>
                <Table.Td>{percent(meta.recall_top)}</Table.Td>
              </Table.Tr>
            </Table.Tbody>
          </Table>
          <Text size="sm" c="dimmed">
            Scored on {count(meta.matched_rows)} contributions matched to DIME version{" "}
            {meta.dime_version ?? DASH}.
          </Text>
        </>
      ) : (
        <Text>
          The live build has not been scored against DIME yet. Its figures appear here once it
          is.
        </Text>
      )}
      {meta.model_version != null && (
        <Text size="sm" c="dimmed">
          Resolved with model <Code>{meta.model_version}</Code>
          {meta.resolver_version != null && (
            <>
              {" "}
              by fundlens{" "}
              <Anchor href={`${REPO}/commit/${meta.resolver_version}`}>
                {meta.resolver_version.slice(0, 7)}
              </Anchor>
            </>
          )}
          {meta.overrides_count != null &&
            `, with ${count(meta.overrides_count)} overrides and ${count(meta.adjudications_applied)} adjudications applied`}
          .
        </Text>
      )}
    </Stack>
  );
}

/** How fundlens counts money and resolves donors, with the live build's figures. */
function MethodologyPage() {
  usePageTitle("Methodology");
  const meta = $api.useQuery("get", "/v1/meta");
  const parts = methodology.split(SLOT);

  return (
    <Stack gap="md" maw={760}>
      {parts.map((part, i) =>
        // `split` with a group puts each slot's name at the odd indexes. Only the prose takes
        // Typography's styles: the slots' tables keep Mantine's own.
        i % 2 === 0 ? (
          <Typography key={i}>
            <Markdown components={components}>{part}</Markdown>
          </Typography>
        ) : (
          <QueryStatus key={i} query={meta}>
            {(data) => SLOTS[part]?.(data)}
          </QueryStatus>
        ),
      )}
    </Stack>
  );
}

export default MethodologyPage;
