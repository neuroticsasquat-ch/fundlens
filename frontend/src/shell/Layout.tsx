import { AppShell, Container, Drawer, Stack } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { Outlet } from "react-router";
import CycleSwitcher from "./CycleSwitcher";
import Footer from "./Footer";
import Header from "./Header";
import RacesLink from "./RacesLink";

/** The shell every page renders inside: header, the phone drawer, the page, the footer. */
function Layout() {
  const [menuOpened, menu] = useDisclosure(false);

  return (
    <AppShell header={{ height: 56 }} padding="md">
      <AppShell.Header>
        <Header menuOpened={menuOpened} onMenu={menu.toggle} />
      </AppShell.Header>
      <Drawer opened={menuOpened} onClose={menu.close} title="fundlens" size="xs" hiddenFrom="sm">
        <Stack>
          <CycleSwitcher onPick={menu.close} />
          <RacesLink onClick={menu.close} />
        </Stack>
      </Drawer>
      <AppShell.Main>
        <Container size="xl">
          <Outlet />
          <Footer />
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}

export default Layout;
