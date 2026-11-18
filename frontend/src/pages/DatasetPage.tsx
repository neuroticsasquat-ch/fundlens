import {
  Alert,
  Anchor,
  Button,
  Code,
  CopyButton,
  Group,
  Select,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { useState } from "react";
import { Link } from "react-router";
import { $api } from "../api/client";
import type { Dataset, DatasetPart, DatasetSnapshot, DatasetTable } from "../api/client";
import DataTable from "../components/DataTable";
import type { Column } from "../components/DataTable";
import QueryStatus from "../components/QueryStatus";
import { count, DASH, fileSize, isoDate, percent } from "../components/format";
import { usePageTitle } from "../components/usePageTitle";

const MANIFEST = "manifest.json";

const cycles = (snapshot: DatasetSnapshot) =>
  snapshot.cycles.length === 1 ? "1 cycle" : `${count(snapshot.cycles.length)} cycles`;

/** `text` in a code block, with a button that copies it. */
function Copyable({ text, label, block = false }: { text: string; label: string; block?: boolean }) {
  const copy = (
    <CopyButton value={text}>
      {({ copied, copy }) => (
        <Button size="compact-xs" variant="light" onClick={copy} aria-label={`Copy ${label}`}>
          {copied ? "Copied" : "Copy"}
        </Button>
      )}
    </CopyButton>
  );
  if (!block) {
    return (
      <Group gap={6} wrap="nowrap">
        <Code>{text}</Code>
        {copy}
      </Group>
    );
  }
  return (
    <Stack gap={4} align="flex-start">
      {copy}
      <Code block w="100%" aria-label={label}>
        {text}
      </Code>
    </Stack>
  );
}

// The README's one-liners (docs/dataset/README.md, "Reading it"), for one cycle of `base`. HTTPS has no
// directory listing, so both list the files from `manifest.json` rather than glob.
const duckdb = (base: string, cycle: number) => `duckdb -c "
SET VARIABLE files = (
  SELECT list('${base}' || f.path)
  FROM (SELECT unnest(tables.contribution.files) AS f
        FROM read_json('${base}${MANIFEST}'))
  WHERE f.path LIKE 'contribution/cycle=${cycle}/%');
SELECT count(*) AS contributions, sum(amount) AS dollars
FROM read_parquet(getvariable('files'));
"`;

const pandas = (base: string, cycle: number) => `import json, urllib.request
import pandas as pd

base = "${base}"
manifest = json.load(urllib.request.urlopen(base + "${MANIFEST}"))
races = pd.concat(
    pd.read_parquet(base + f["path"])
    for f in manifest["tables"]["race"]["files"]
    if f["path"].startswith("race/cycle=${cycle}/")
)`;

/**
 * Where one table's files for the cycle are: a link to the file when there is one, which a
 * browser downloads; else the directory's address, which a browser cannot list, to copy.
 */
function Part({ snapshot, part }: { snapshot: DatasetSnapshot; part: DatasetPart | undefined }) {
  if (part === undefined) return DASH;
  const url = snapshot.url + part.path;
  if (part.files === 1) {
    return (
      <Group gap={6} wrap="nowrap">
        <Anchor href={url}>{part.path}</Anchor>
        <Text size="xs" c="dimmed" span>
          {fileSize(part.bytes)}
        </Text>
      </Group>
    );
  }
  return (
    <Stack gap={2}>
      <Copyable text={url} label={`${part.path} address`} />
      <Text size="xs" c="dimmed">
        {count(part.files)} files, {fileSize(part.bytes)}, each listed in{" "}
        <Anchor href={snapshot.url + MANIFEST} size="xs">
          {MANIFEST}
        </Anchor>
      </Text>
    </Stack>
  );
}

function tableColumns(
  snapshot: DatasetSnapshot,
  cycle: number,
  baseUrl: string,
): Column<DatasetTable>[] {
  return [
    {
      key: "name",
      header: "Table",
      render: (table) => (
        <Stack gap={0}>
          <Code>{table.name}</Code>
          <Anchor href={`${baseUrl}schema/${table.name}.json`} size="xs">
            schema
          </Anchor>
        </Stack>
      ),
      sortValue: (table) => table.name,
    },
    {
      key: "rows",
      header: "Rows, every cycle",
      align: "right",
      render: (table) => count(table.rows),
      sortValue: (table) => table.rows,
    },
    {
      key: "bytes",
      header: "Size, every cycle",
      align: "right",
      render: (table) => fileSize(table.bytes),
      sortValue: (table) => table.bytes,
    },
    {
      key: "files",
      header: `Files for ${cycle}`,
      // A table with no cycle (`donor`, `crosswalk`) is one file for every cycle.
      render: (table) => (
        <Part
          snapshot={snapshot}
          part={table.parts.find((part) => part.cycle === cycle || part.cycle === null)}
        />
      ),
    },
  ];
}

const PREVIOUS_COLUMNS: Column<DatasetSnapshot>[] = [
  {
    key: "date",
    header: "Snapshot",
    render: (snapshot) => isoDate(snapshot.snapshot_date),
    sortValue: (snapshot) => snapshot.snapshot_date,
  },
  {
    key: "build",
    header: "Build",
    render: (snapshot) => <Code>{snapshot.build_id}</Code>,
  },
  {
    key: "cycles",
    header: "Cycles",
    align: "right",
    render: (snapshot) => count(snapshot.cycles.length),
    sortValue: (snapshot) => snapshot.cycles.length,
  },
  {
    key: "precision",
    header: "Precision",
    align: "right",
    render: (snapshot) => percent(snapshot.precision),
  },
  {
    key: "recall",
    header: "Recall",
    align: "right",
    render: (snapshot) => percent(snapshot.recall),
  },
  {
    key: "manifest",
    header: "Files",
    render: (snapshot) => <Anchor href={snapshot.url + MANIFEST}>{MANIFEST}</Anchor>,
  },
];

/** The newest snapshot, its tables, how to read them, and the ones before it. */
function Snapshots({ data }: { data: Dataset }) {
  const [shown, ...previous] = data.snapshots;
  const [chosen, setChosen] = useState<number | undefined>(undefined);

  if (shown === undefined) {
    return <Text>No snapshot is published yet. The first follows a weekly build.</Text>;
  }
  const cycle = chosen !== undefined && shown.cycles.includes(chosen) ? chosen : shown.cycles[0];
  // `latest/` once it holds the newest snapshot; while it is still being copied, the dated one.
  const inLatest = data.latest === shown.snapshot_date;
  const latest = `${data.base_url}latest/`;
  const readFrom = inLatest ? latest : shown.url;

  return (
    <Stack gap="lg">
      <Text>
        Licensed{" "}
        <Anchor href={`${data.base_url}LICENSE`}>{shown.license}</Anchor>. Credit it as{" "}
        <Text span fw={500}>
          {shown.attribution}
        </Text>
        . The <Anchor href={`${data.base_url}README.md`}>README</Anchor> describes every table
        and links each one's column schema; the{" "}
        <Anchor href={`${data.base_url}CHANGELOG.md`}>changelog</Anchor> lists every change to
        them. How the money is counted and donors resolved is on the{" "}
        <Anchor component={Link} to="/methodology">
          methodology page
        </Anchor>
        .
      </Text>

      <Stack gap="sm">
        <Title order={2}>Snapshot of {isoDate(shown.snapshot_date)}</Title>
        <Text size="sm" c="dimmed">
          Build <Code>{shown.build_id}</Code> · {cycles(shown)} ·{" "}
          {shown.precision == null
            ? "resolution not yet scored against DIME"
            : `resolution precision ${percent(shown.precision)}, recall ${percent(shown.recall)} against DIME`}{" "}
          · every file with its size and SHA-256 in{" "}
          <Anchor href={shown.url + MANIFEST} size="sm">
            {MANIFEST}
          </Anchor>
          {inLatest && (
            <>
              {" "}
              · also at <Code>{latest}</Code>
            </>
          )}
        </Text>
        {cycle !== undefined && (
          <Group>
            <Select
              label="Show cycle"
              data={shown.cycles.map((c) => ({ value: String(c), label: String(c) }))}
              value={String(cycle)}
              onChange={(value) => value && setChosen(Number(value))}
              allowDeselect={false}
              w={140}
            />
          </Group>
        )}
        <DataTable
          caption={`Tables of the snapshot of ${isoDate(shown.snapshot_date)}`}
          columns={tableColumns(shown, cycle ?? 0, data.base_url)}
          rows={shown.tables}
          rowKey={(table) => table.name}
        />
      </Stack>

      {cycle !== undefined && (
        <Stack gap="sm">
          <Title order={2}>Reading it</Title>
          <Text>
            Over HTTPS a directory cannot be listed, so a <Code>*.parquet</Code> glob does not
            work: read the file list from <Code>{MANIFEST}</Code>. Every {cycle} contribution, in
            DuckDB:
          </Text>
          <Copyable text={duckdb(readFrom, cycle)} label="DuckDB one-liner" block />
          <Text>Its races, in pandas (with pyarrow):</Text>
          <Copyable text={pandas(readFrom, cycle)} label="pandas one-liner" block />
          <Text size="sm" c="dimmed">
            A per-IP rate limit applies. For a whole table or the whole dataset, download the
            files once and read them locally; the README shows how.
          </Text>
        </Stack>
      )}

      <Stack gap="sm">
        <Title order={2}>Previous snapshots</Title>
        <Text size="sm" c="dimmed">
          A snapshot is taken weekly; the newest 8 are kept.
        </Text>
        <DataTable
          caption="Earlier snapshots"
          columns={PREVIOUS_COLUMNS}
          rows={previous}
          rowKey={(snapshot) => snapshot.snapshot_date}
          emptyMessage="None yet: this is the first."
        />
      </Stack>
    </Stack>
  );
}

/** The open dataset: what it is, its latest snapshot's files, and how to read them. */
function DatasetPage() {
  usePageTitle("Dataset");
  const dataset = $api.useQuery("get", "/v1/dataset");

  return (
    <Stack gap="md" maw={1000}>
      <Title order={1}>Dataset</Title>
      <Text>
        Everything fundlens shows, as open Parquet files: every federal contribution, committee,
        candidate, race, committee transfer, organization's gift and independent expenditure
        since 1980, from the FEC's bulk files, with individual donors resolved across the name,
        employer and address variants they are reported under. A new snapshot follows each
        weekly build.
      </Text>
      <Alert color="yellow" title="Contributor information and the FEC">
        Federal law limits how contributor information may be used, whatever this dataset's
        license (52 U.S.C. 30111(a)(4), 11 CFR 104.15): information copied from reports filed
        with the FEC may not be sold or used for the purpose of soliciting contributions or for
        commercial purposes, other than using the name and address of a political committee to
        solicit contributions from that committee. This is not legal advice.
      </Alert>
      <QueryStatus query={dataset}>{(data) => <Snapshots data={data} />}</QueryStatus>
    </Stack>
  );
}

export default DatasetPage;
