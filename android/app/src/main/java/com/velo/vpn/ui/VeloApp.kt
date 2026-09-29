package com.velo.vpn.ui

import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.velo.vpn.VeloApplication
import com.velo.vpn.ui.screens.*

object Routes {
    const val Home = "home"
    const val Gifts = "gifts"
    const val Report = "report"
    const val Settings = "settings"
    const val Premium = "premium"
    const val Servers = "servers"
    const val Missions = "missions"
    const val Referral = "referral"
    const val Support = "support"
    const val Payment = "payment/{kind}?plan={plan}&amount={amount}"
    fun payment(kind: String, plan: String = "", amount: Int = 0) = "payment/$kind?plan=$plan&amount=$amount"
    const val Account = "account"
    const val Store = "store"
}

@Composable
fun VeloApp() {
    val nav = rememberNavController()
    val app = LocalContext.current.applicationContext as VeloApplication
    val veloViewModel: VeloViewModel = viewModel(factory = VeloViewModel.Factory(app.container))
    val accountViewModel: AccountViewModel = viewModel(factory = AccountViewModel.Factory(app.container))
    val rewardsViewModel: RewardsViewModel = viewModel(factory = RewardsViewModel.Factory(app.container))
    val commerceViewModel: CommerceViewModel = viewModel(factory = CommerceViewModel.Factory(app.container))
    val storeViewModel: StoreViewModel = viewModel(factory = StoreViewModel.Factory(app.container))

    NavHost(navController = nav, startDestination = Routes.Home) {
        composable(Routes.Home) { HomeScreen(nav, veloViewModel, accountViewModel) }
        composable(Routes.Gifts) { GiftsScreen(nav, accountViewModel) }
        composable(Routes.Report) {
            val reportVm: ReportViewModel = viewModel(factory = ReportViewModel.Factory(app.container))
            ReportScreen(nav, reportVm, accountViewModel)
        }
        composable(Routes.Settings) { SettingsScreen(nav, accountViewModel) }
        composable(Routes.Account) { AccountScreen(nav, accountViewModel) }
        composable(Routes.Premium) { PremiumScreen(nav, commerceViewModel, accountViewModel) }
        composable(Routes.Servers) { ServerScreen(nav, veloViewModel) }
        composable(Routes.Missions) { MissionsScreen(nav, rewardsViewModel, accountViewModel) }
        composable(Routes.Referral) { ReferralScreen(nav, rewardsViewModel, accountViewModel) }
        composable(Routes.Support) { SupportScreen(nav, commerceViewModel, accountViewModel) }
        composable(Routes.Store) { StoreScreen(nav, storeViewModel, accountViewModel, veloViewModel) }
        composable(
            Routes.Payment,
            arguments = listOf(
                navArgument("kind") { type = NavType.StringType },
                navArgument("plan") { type = NavType.StringType; defaultValue = "" },
                navArgument("amount") { type = NavType.IntType; defaultValue = 0 },
            ),
        ) {
            ManualPaymentScreen(
                nav = nav,
                kind = it.arguments?.getString("kind") ?: "support",
                planCode = it.arguments?.getString("plan")?.ifBlank { null },
                baseAmount = it.arguments?.getInt("amount") ?: 0,
                commerce = commerceViewModel,
                account = accountViewModel,
            )
        }
    }
}
