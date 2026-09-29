package com.velo.vpn.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AllInclusive
import androidx.compose.material.icons.filled.Block
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.Dns
import androidx.compose.material.icons.filled.WorkspacePremium
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.velo.vpn.ui.AccountViewModel
import com.velo.vpn.ui.CommerceViewModel
import com.velo.vpn.ui.Routes
import com.velo.vpn.ui.components.FeatureRow
import com.velo.vpn.ui.components.PrimaryButton
import com.velo.vpn.ui.components.VeloHeader
import com.velo.vpn.ui.theme.Muted
import com.velo.vpn.ui.theme.VeloPurple

private data class PremiumPlanUi(val code: String, val title: String, val fallback: Int, val recommended: Boolean = false)

@Composable
fun PremiumScreen(nav: NavHostController, commerce: CommerceViewModel, account: AccountViewModel) {
    val commerceState by commerce.state.collectAsState()
    val accountState by account.state.collectAsState()
    val plans = listOf(
        PremiumPlanUi("15d", "۱۵ روزه", 189000),
        PremiumPlanUi("1m", "۱ ماهه", 349000),
        PremiumPlanUi("3m", "۳ ماهه", 949000, true),
        PremiumPlanUi("6m", "۶ ماهه", 1749000),
    )
    var selected by remember { mutableIntStateOf(2) }
    val config = commerceState.config
    val current = plans[selected]
    val price = config?.premiumPrices?.get(current.code) ?: current.fallback

    Scaffold { pad ->
        Column(
            Modifier.fillMaxSize().padding(pad).padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            VeloHeader(showBack = true, hearts = accountState.hearts, onBack = { nav.popBackStack() })
            Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                Icon(Icons.Default.WorkspacePremium, null, tint = VeloPurple, modifier = Modifier.size(88.dp))
            }
            Text("پریمیوم", Modifier.align(Alignment.CenterHorizontally), fontSize = 30.sp, fontWeight = FontWeight.ExtraBold)
            Text("تجربه‌ای سریع‌تر، بدون محدودیت و بدون تبلیغ", Modifier.align(Alignment.CenterHorizontally), color = Muted)
            FeatureRow(Icons.Default.AllInclusive, "بدون محدودیت زمان", "اتصال بدون محدودیت")
            FeatureRow(Icons.Default.Bolt, "سرعت کامل", "بدون محدودیت سرعت از سمت Velo")
            FeatureRow(Icons.Default.Block, "بدون تبلیغ", "تجربه‌ای آرام و بدون مزاحمت")
            FeatureRow(Icons.Default.Dns, "انتخاب سرور", "دسترسی به سرورهای Premium")

            Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                plans.forEachIndexed { i, p ->
                    val pPrice = config?.premiumPrices?.get(p.code) ?: p.fallback
                    FilterChip(
                        selected = selected == i,
                        onClick = { selected = i },
                        label = {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Text(p.title, fontWeight = FontWeight.Bold)
                                Text(formatToman(pPrice), fontSize = 10.sp)
                            }
                        },
                        modifier = Modifier.weight(1f),
                    )
                }
            }
            if (current.recommended) Text("پیشنهاد Velo", color = VeloPurple, fontSize = 11.sp, fontWeight = FontWeight.Bold)

            PrimaryButton(if (accountState.loggedIn) "خرید اشتراک" else "ورود و خرید اشتراک") {
                if (!accountState.loggedIn) nav.navigate(Routes.Account)
                else nav.navigate(Routes.payment("premium", current.code, price))
            }
            Text(
                "در مرحله پرداخت می‌توانید با قلب‌ها تا سقف ${config?.maxHeartDiscountPercent ?: 30}٪ تخفیف بگیرید.",
                color = Muted,
                fontSize = 11.sp,
            )
        }
    }
}

private fun formatToman(value: Int): String = "%,d تومان".format(value)
