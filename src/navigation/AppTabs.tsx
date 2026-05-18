import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text } from 'react-native';
import { CadastrosScreen } from '../screens/CadastrosScreen';
import { DashboardScreen } from '../screens/DashboardScreen';
import { WithdrawalsScreen } from '../screens/WithdrawalsScreen';

const Tab = createBottomTabNavigator();

function TabIcon({ label, color }: { label: string; color: string }) {
  return <Text style={{ color, fontSize: 16, fontWeight: '700' }}>{label}</Text>;
}

export function AppTabs() {
  return (
    <Tab.Navigator>
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{ tabBarIcon: ({ color }) => <TabIcon label="D" color={color} /> }}
      />
      <Tab.Screen
        name="Retiradas"
        component={WithdrawalsScreen}
        options={{ tabBarIcon: ({ color }) => <TabIcon label="R" color={color} /> }}
      />
      <Tab.Screen
        name="Cadastros"
        component={CadastrosScreen}
        options={{ tabBarIcon: ({ color }) => <TabIcon label="C" color={color} /> }}
      />
    </Tab.Navigator>
  );
}
