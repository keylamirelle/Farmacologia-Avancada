import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuth } from '../context/AuthContext';
import { LoginScreen } from '../screens/LoginScreen';
import { ProductFormScreen } from '../screens/ProductFormScreen';
import { EntryScreen } from '../screens/EntryScreen';
import { WithdrawalScreen } from '../screens/WithdrawalScreen';
import { AppTabs } from './AppTabs';

export type RootStackParamList = {
  Login: undefined;
  Tabs: undefined;
  ProductForm: { productId?: string };
  Entry: { productId?: string };
  Withdrawal: { productId?: string };
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export function RootNavigator() {
  const { session } = useAuth();

  return (
    <NavigationContainer>
      {session ? (
        <Stack.Navigator>
          <Stack.Screen name="Tabs" component={AppTabs} options={{ headerShown: false }} />
          <Stack.Screen
            name="ProductForm"
            component={ProductFormScreen}
            options={({ route }) => ({
              title: route.params?.productId ? 'Editar produto' : 'Novo produto',
            })}
          />
          <Stack.Screen name="Entry" component={EntryScreen} options={{ title: 'Entrada de estoque' }} />
          <Stack.Screen
            name="Withdrawal"
            component={WithdrawalScreen}
            options={{ title: 'Retirada' }}
          />
        </Stack.Navigator>
      ) : (
        <Stack.Navigator>
          <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
        </Stack.Navigator>
      )}
    </NavigationContainer>
  );
}
