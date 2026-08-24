/**
 * Switches between light, dark and the operating system's setting.
 *
 * Three states rather than two on purpose. A plain light/dark switch has no
 * way back to "follow my system", so someone who has their laptop set to go
 * dark in the evening loses that the first time they touch the control.
 *
 * MUI persists the choice and applies it by setting an attribute on <html>,
 * which is also what the inline script in index.html reads on the next visit
 * to avoid a flash of the wrong scheme.
 */

import { DarkMode, LightMode, SettingsBrightness } from '@mui/icons-material';
import { IconButton, Menu, MenuItem, ListItemIcon, ListItemText, Tooltip } from '@mui/material';
import { useColorScheme } from '@mui/material/styles';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

type Mode = 'light' | 'dark' | 'system';

const OPTIONS: { value: Mode; labelKey: string; Icon: typeof LightMode }[] = [
  { value: 'light', labelKey: 'themeLight', Icon: LightMode },
  { value: 'dark', labelKey: 'themeDark', Icon: DarkMode },
  { value: 'system', labelKey: 'themeSystem', Icon: SettingsBrightness },
];

export default function ColorSchemeToggle() {
  const { t } = useTranslation();
  const { mode, setMode } = useColorScheme();
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);

  // Undefined until the provider has read the stored preference. Rendering a
  // guessed icon first would flip it a moment later, which reads as a glitch.
  if (!mode) return null;

  const current = OPTIONS.find((option) => option.value === mode) ?? OPTIONS[2];
  const CurrentIcon = current.Icon;

  return (
    <>
      <Tooltip title={t('themeLabel')}>
        <IconButton
          color="inherit"
          onClick={(event) => setAnchorEl(event.currentTarget)}
          aria-label={t('themeLabel')}
          aria-haspopup="menu"
        >
          <CurrentIcon />
        </IconButton>
      </Tooltip>

      <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
        {OPTIONS.map(({ value, labelKey, Icon }) => (
          <MenuItem
            key={value}
            selected={value === mode}
            onClick={() => {
              setMode(value);
              setAnchorEl(null);
            }}
          >
            <ListItemIcon>
              <Icon fontSize="small" />
            </ListItemIcon>
            <ListItemText>{t(labelKey)}</ListItemText>
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}
