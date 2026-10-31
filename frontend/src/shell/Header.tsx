import { Anchor, Box, Burger, Group } from "@mantine/core";
import { Link } from "react-router";
import SearchBox from "../search/SearchBox";
import CycleSwitcher from "./CycleSwitcher";
import RacesLink from "./RacesLink";

/**
 * Brand, cycle switcher, search and the Races link; below `sm` the switcher and the link move
 * into the drawer the Burger opens, and the search box stays.
 */
function Header({ menuOpened, onMenu }: { menuOpened: boolean; onMenu: () => void }) {
  return (
    <Group h="100%" px="md" gap="md" wrap="nowrap">
      <Anchor component={Link} to="/" fw={700} fz="lg" underline="never" c="inherit">
        fundlens
      </Anchor>
      <Box visibleFrom="sm">
        <CycleSwitcher />
      </Box>
      <Box style={{ flex: 1 }}>
        <SearchBox />
      </Box>
      <Box visibleFrom="sm">
        <RacesLink />
      </Box>
      <Burger
        opened={menuOpened}
        onClick={onMenu}
        hiddenFrom="sm"
        size="sm"
        aria-label="Open navigation"
      />
    </Group>
  );
}

export default Header;
