package com.velo.vpn.ui.screens

import android.content.Intent
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.velo.vpn.ui.AccountViewModel
import com.velo.vpn.ui.RewardsViewModel
import com.velo.vpn.ui.Routes
import com.velo.vpn.ui.components.PrimaryButton
import com.velo.vpn.ui.components.VeloCard
import com.velo.vpn.ui.components.VeloHeader
import com.velo.vpn.ui.theme.Muted
import com.velo.vpn.ui.theme.VeloPurple

@Composable
fun ReferralScreen(nav: NavHostController, vm: RewardsViewModel, accountVm: AccountViewModel) {
    val state by vm.state.collectAsState()
    val account by accountVm.state.collectAsState()
    val context = LocalContext.current
    LaunchedEffect(Unit) { vm.refreshReferrals() }
    val referral = state.referrals

    Scaffold { pad ->
        Column(
            Modifier.fillMaxSize().padding(pad).padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            VeloHeader(showBack = true, hearts = account.hearts, onBack = { nav.popBackStack() })
            Text("دعوت دوستان", fontSize = 30.sp, fontWeight = FontWeight.ExtraBold)
            Text("دوستانتان را دعوت کنید و برای نصب و استفاده واقعی آن‌ها قلب بگیرید.", color = Muted)

            if (state.loadingReferrals) LinearProgressIndicator(Modifier.fillMaxWidth())
            if (referral == null && !state.loadingReferrals) {
                VeloCard(Modifier.fillMaxWidth()) {
                    Text("برای داشتن لینک دعوت شخصی باید با ایمیل وارد حساب Velo شوید.", fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(12.dp))
                    PrimaryButton("ورود با ایمیل") { nav.navigate(Routes.Account) }
                }
            }
            if (referral != null) {
                VeloCard(Modifier.fillMaxWidth()) {
                    Text("لینک دعوت شما", fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(10.dp))
                    OutlinedTextField(
                        value = referral.shareUrl,
                        onValueChange = {},
                        readOnly = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Spacer(Modifier.height(10.dp))
                    PrimaryButton("اشتراک‌گذاری لینک دعوت") {
                        val intent = Intent(Intent.ACTION_SEND).apply {
                            type = "text/plain"
                            putExtra(Intent.EXTRA_TEXT, "Velo را با لینک من نصب کن: ${referral.shareUrl}")
                        }
                        context.startActivity(Intent.createChooser(intent, "دعوت با Velo"))
                    }
                }
                VeloCard(Modifier.fillMaxWidth()) {
                    Text("نحوه پاداش", fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(8.dp))
                    Text("نصب موفق: +${referral.installRewardHearts} ♥", color = Muted)
                    Text("هر روز استفاده واقعی در ۷ روز اول: +${referral.dailyRewardHearts} ♥", color = Muted)
                }
                Text("دوستان دعوت‌شده", fontWeight = FontWeight.Bold, fontSize = 17.sp)
                if (referral.items.isEmpty()) Text("هنوز دوستی از لینک شما فعال نشده است.", color = Muted)
                referral.items.forEach { friend ->
                    VeloCard(Modifier.fillMaxWidth()) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Person, null, tint = VeloPurple)
                            Spacer(Modifier.width(10.dp))
                            Column(Modifier.weight(1f)) {
                                Text(friend.label, fontWeight = FontWeight.Bold)
                                val status = when {
                                    friend.complete -> "۷ روز کامل شد"
                                    friend.installed -> "روز ${friend.rewardedDays} از ۷"
                                    else -> "در انتظار نصب"
                                }
                                Text(status, color = Muted, fontSize = 11.sp)
                            }
                            val earned = (if (friend.installed) referral.installRewardHearts else 0) + friend.rewardedDays * referral.dailyRewardHearts
                            Text(if (earned > 0) "+$earned ♥" else "—", color = VeloPurple, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
            state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        }
    }
}
