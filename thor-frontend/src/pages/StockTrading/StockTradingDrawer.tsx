import {
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
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
} from '@mui/icons-material';
import { DEFAULT_WIDTH_OPEN, DEFAULT_WIDTH_CLOSED } from '../../components/CollapsibleDrawer';

interface StockTradingDrawerProps {
  open: boolean;
  onToggle: () => void;
  widthOpen?: number;
  widthClosed?: number;
}

const defaultItems = [
  { label: 'Overview', icon: <AssessmentIcon /> },
  { label: 'Orders', icon: <ReceiptLongIcon /> },
  { label: 'Positions', icon: <ListAltIcon /> },
  { label: 'History', icon: <HistoryIcon /> },
];

const StockTradingDrawer: React.FC<StockTradingDrawerProps> = ({
  open,
  onToggle,
  widthOpen = DEFAULT_WIDTH_OPEN,
  widthClosed = DEFAULT_WIDTH_CLOSED,
}) => {
  const drawerWidth = open ? widthOpen : widthClosed;

  return (
    <Drawer
      variant="permanent"
      anchor="right"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        whiteSpace: 'nowrap',
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
          overflowX: 'hidden',
          transition: 'width 200ms ease',
          background: 'linear-gradient(180deg, #111725 0%, #05070b 100%)',
          borderLeft: '1px solid rgba(255, 255, 255, 0.08)',
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

      <List sx={{ mt: 1 }}>
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
