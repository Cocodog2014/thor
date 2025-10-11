import {
  Box,
  Drawer,
  FormControl,
  IconButton,
  InputLabel,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  MenuItem,
  Select,
  Toolbar,
  Typography,
} from '@mui/material';
import {
  Assessment as AssessmentIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  History as HistoryIcon,
  ListAlt as ListAltIcon,
  ReceiptLong as ReceiptLongIcon,
  VisibilityOutlined as VisibilityIcon,
} from '@mui/icons-material';
import { DEFAULT_WIDTH_OPEN, DEFAULT_WIDTH_CLOSED } from '../../components/CollapsibleDrawer';
import type { SelectChangeEvent } from '@mui/material/Select';

type DrawerTradingMode = 'live' | 'paper';

interface StockTradingDrawerProps {
  open: boolean;
  onToggle: () => void;
  widthOpen?: number;
  widthClosed?: number;
  mode: DrawerTradingMode;
  onModeChange: (value: DrawerTradingMode) => void;
}

const defaultItems = [
  { label: 'Overview', icon: <AssessmentIcon /> },
  { label: 'Orders', icon: <ReceiptLongIcon /> },
  { label: 'Watch List', icon: <VisibilityIcon /> },
  { label: 'Positions', icon: <ListAltIcon /> },
  { label: 'History', icon: <HistoryIcon /> },
];

const StockTradingDrawer: React.FC<StockTradingDrawerProps> = ({
  open,
  onToggle,
  mode,
  onModeChange,
  widthOpen = DEFAULT_WIDTH_OPEN,
  widthClosed = DEFAULT_WIDTH_CLOSED,
}) => {
  const drawerWidth = open ? widthOpen : widthClosed;

  const handleChange = (event: SelectChangeEvent) => {
    onModeChange(event.target.value as DrawerTradingMode);
  };

  return (
    <Drawer
      variant="permanent"
      anchor="right"
      sx={{
        pointerEvents: 'none',
        width: 0,
        '& .MuiDrawer-paper': {
          pointerEvents: 'auto',
          width: drawerWidth,
          boxSizing: 'border-box',
          overflowX: 'hidden',
          transition: 'width 200ms ease',
          background: 'linear-gradient(180deg, #111725 0%, #05070b 100%)',
          borderLeft: '1px solid rgba(255, 255, 255, 0.08)',
          position: 'fixed',
          right: 0,
          top: 0,
          height: '100vh',
          zIndex: (theme) => theme.zIndex.drawer + 1,
        },
      }}
    >
      <Toolbar
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: open ? 'space-between' : 'center',
          px: 1,
          minHeight: '64px !important',
        }}
      >
        {open && (
          <Typography
            variant="subtitle1"
            sx={{
              fontFamily: 'var(--thor-font-title)',
              textTransform: 'uppercase',
              letterSpacing: '0.12em',
              color: 'var(--thor-blue-light)',
            }}
          >
            Stock Desk
          </Typography>
        )}
        <IconButton onClick={onToggle} sx={{ color: 'var(--thor-blue-light)' }} aria-label={open ? 'Collapse stock drawer' : 'Expand stock drawer'}>
          {open ? <ChevronRightIcon /> : <ChevronLeftIcon />}
        </IconButton>
      </Toolbar>

      {open && (
        <Box sx={{ px: 2, pb: 2 }}>
          <FormControl
            fullWidth
            size="small"
            sx={{
              '& .MuiOutlinedInput-root': {
                backgroundColor: 'rgba(5, 7, 11, 0.95)',
                borderRadius: 2,
                '& fieldset': {
                  borderColor: 'rgba(66, 165, 245, 0.4)',
                },
                '&:hover fieldset': {
                  borderColor: 'rgba(66, 165, 245, 0.6)',
                },
                '&.Mui-focused fieldset': {
                  borderColor: 'var(--thor-blue-light)',
                },
              },
              '& .MuiInputLabel-root': {
                color: 'rgba(255, 255, 255, 0.7)',
              },
            }}
          >
            <InputLabel id="stock-trading-mode">Trading Mode</InputLabel>
            <Select
              labelId="stock-trading-mode"
              value={mode}
              label="Trading Mode"
              onChange={handleChange}
              MenuProps={{
                PaperProps: {
                  sx: {
                    backgroundColor: 'rgba(5, 7, 11, 0.98)',
                    border: '1px solid rgba(66, 165, 245, 0.35)',
                    '& .MuiMenuItem-root': {
                      color: '#fff',
                      '&:hover': {
                        backgroundColor: 'rgba(66, 165, 245, 0.18)',
                      },
                      '&.Mui-selected': {
                        backgroundColor: 'rgba(66, 165, 245, 0.25)',
                        '&:hover': {
                          backgroundColor: 'rgba(66, 165, 245, 0.35)',
                        },
                      },
                    },
                  },
                },
              }}
            >
              <MenuItem value="live">Live Trading</MenuItem>
              <MenuItem value="paper">Paper Trading</MenuItem>
            </Select>
          </FormControl>
        </Box>
      )}

      <List sx={{ mt: open ? 0 : 1 }}>
        {defaultItems.map((item) => (
          <ListItem key={item.label} disablePadding sx={{ display: 'block' }}>
            <ListItemButton
              sx={{
                minHeight: 48,
                justifyContent: open ? 'initial' : 'center',
                px: 2.5,
                '&:hover': {
                  backgroundColor: 'rgba(66, 165, 245, 0.1)',
                },
              }}
            >
              <ListItemIcon
                sx={{
                  minWidth: 0,
                  mr: open ? 3 : 'auto',
                  justifyContent: 'center',
                  color: 'var(--thor-blue-light)',
                }}
              >
                {item.icon}
              </ListItemIcon>
              <ListItemText
                primary={item.label}
                sx={{
                  opacity: open ? 1 : 0,
                  color: 'rgba(255, 255, 255, 0.85)',
                }}
              />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Drawer>
  );
};

export default StockTradingDrawer;
