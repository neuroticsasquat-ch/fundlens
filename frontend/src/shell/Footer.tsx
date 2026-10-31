import { Anchor, Box, Group, Stack, Text } from "@mantine/core";
import { Link } from "react-router";
import { $api } from "../api/client";
import { isoDate } from "../components/format";
import { buildSha } from "../config";

/** Where the data came from and on what terms, and the build the bundle is. */
function Footer() {
  const meta = $api.useQuery("get", "/v1/meta");

  return (
    <Box
      component="footer"
      mt="xl"
      pt="md"
      style={{ borderTop: "1px solid var(--mantine-color-default-border)" }}
    >
      <Stack gap={6}>
        <Group gap="xs" fz="sm">
          <Anchor component={Link} to="/dataset">
            Dataset
          </Anchor>
          <Text c="dimmed" span>
            ·
          </Text>
          <Anchor component={Link} to="/methodology">
            Methodology
          </Anchor>
          <Text c="dimmed" span>
            ·
          </Text>
          <Anchor href="https://github.com/neuroticsasquat-ch/fundlens">GitHub</Anchor>
          <Text c="dimmed" span>
            ·
          </Text>
          <Anchor href="https://api.fundlens.org/docs">API</Anchor>
        </Group>
        {meta.data && (
          <Text size="xs" c="dimmed">
            Source: FEC bulk data · build {meta.data.build_id} published{" "}
            {isoDate(meta.data.published_at)}
          </Text>
        )}
        <Text size="xs" c="dimmed">
          Contributor information may not be sold or used for commercial purposes or to solicit
          contributions (11 CFR 104.15). Dataset: CC BY 4.0.
        </Text>
        <Text size="xs" c="dimmed">
          fundlens · build {buildSha}
        </Text>
      </Stack>
    </Box>
  );
}

export default Footer;
