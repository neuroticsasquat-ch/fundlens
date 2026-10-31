import { Combobox, Text, TextInput, useCombobox } from "@mantine/core";
import type { MantineSize } from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { useState } from "react";
import type { KeyboardEvent } from "react";
import { useNavigate } from "react-router";
import { $api } from "../api/client";
import type { SearchResult } from "../api/client";
import { groupByKind, searchAliases, searchTarget } from "./target";

// The API's `q` minimum; below it the box shows no dropdown and sends no request.
export const MIN_QUERY = 2;
const ALL_RESULTS = "all";

/**
 * The search typeahead (spec NEU-2043 §4.3): hits grouped by kind as you type, Enter opens the
 * highlighted hit or, with none highlighted, the best one; the last option opens `/search`.
 */
function SearchBox({ size, autoFocus }: { size?: MantineSize; autoFocus?: boolean }) {
  const navigate = useNavigate();
  const [value, setValue] = useState("");
  const typed = value.trim();
  const [q] = useDebouncedValue(typed, 250);
  const combobox = useCombobox({ onDropdownClose: () => combobox.resetSelectedOption() });
  const search = $api.useQuery(
    "get",
    "/v1/search",
    { params: { query: { q } } },
    { enabled: q.length >= MIN_QUERY },
  );
  // Results for what is in the box now, not for what was typed before the debounce caught up.
  const results = q === typed ? search.data : undefined;

  const go = (to: string) => {
    navigate(to);
    setValue("");
    combobox.closeDropdown();
  };
  const searchPage = () => go(`/search?q=${encodeURIComponent(typed)}`);
  const open = (result: SearchResult) => go(searchTarget(result));

  const submit = (option: string) => {
    if (option === ALL_RESULTS) return searchPage();
    const hit = results?.[Number(option)];
    if (hit) open(hit);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== "Enter" || event.nativeEvent.isComposing) return;
    // A highlighted option is the combobox's to open.
    if (combobox.dropdownOpened && combobox.getSelectedOptionIndex() !== -1) return;
    event.preventDefault();
    const top = typed.length >= MIN_QUERY ? results?.[0] : undefined;
    if (top) open(top);
    else searchPage();
  };

  const allResults = (
    <Combobox.Option value={ALL_RESULTS}>
      <Text size="sm">All results for ‘{typed}’</Text>
    </Combobox.Option>
  );

  return (
    <Combobox store={combobox} onOptionSubmit={submit}>
      <Combobox.Target>
        <TextInput
          aria-label="Search"
          placeholder="Search races, candidates, committees"
          size={size}
          autoFocus={autoFocus}
          value={value}
          onChange={(event) => {
            setValue(event.currentTarget.value);
            combobox.openDropdown();
            combobox.resetSelectedOption();
          }}
          onKeyDown={onKeyDown}
          onFocus={() => combobox.openDropdown()}
          onBlur={() => combobox.closeDropdown()}
        />
      </Combobox.Target>

      <Combobox.Dropdown hidden={typed.length < MIN_QUERY}>
        <Combobox.Options aria-label="Search results">
          {typed.length < MIN_QUERY ? null : results === undefined ? (
            <Combobox.Empty>Searching…</Combobox.Empty>
          ) : results.length === 0 ? (
            <>
              <Combobox.Empty>No results for ‘{typed}’</Combobox.Empty>
              {allResults}
            </>
          ) : (
            <>
              {groupByKind(results).map((group) => (
                <Combobox.Group key={group.kind} label={group.label}>
                  {group.hits.map(({ result, index }) => {
                    const aliases = searchAliases(result);
                    return (
                      <Combobox.Option key={`${result.kind}:${result.id}`} value={String(index)}>
                        <Text size="sm">{result.name}</Text>
                        {aliases && (
                          <Text size="xs" c="dimmed">
                            {aliases}
                          </Text>
                        )}
                      </Combobox.Option>
                    );
                  })}
                </Combobox.Group>
              ))}
              {allResults}
            </>
          )}
        </Combobox.Options>
      </Combobox.Dropdown>
    </Combobox>
  );
}

export default SearchBox;
