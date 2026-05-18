import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text } from 'react-native';
import { ProductsScreen } from '../screens/ProductsScreen';
import { HistoryScreen } from '../screens/HistoryScreen';

const Tab = createBottomTabNavigator();

function TabIcon({ label, color }: { label: string; color: string }) {
  return <Text style={{ color, fontSize: 18 }}>{label}</Text>;
}

export function AppTabs() {
  return (
    <Tab.Navigator>
      <Tab.Screen
        name="Produtos"
        component={ProductsScreen}
        options={{
          tabBarIcon: ({ color }) => <TabIcon label="P" color={color} />,
        }}
      />
      <Tab.Screen
        name="Historico"
        component={HistoryScreen}
        options={{
          title: 'Historico',
          tabBarIcon: ({ color }) => <TabIcon label="H" color={color} />,
        }}
      />
    </Tab.Navigator>
  );
}
